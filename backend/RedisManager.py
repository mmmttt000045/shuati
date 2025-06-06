"""
Redis统一管理器 - 整合所有Redis相关功能
包含session管理、缓存管理、数据存储等功能
"""
import json
import logging
import pickle
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Set, Union

import redis
from flask import session

from .config import RedisConfig, SESSION_KEYS

logger = logging.getLogger(__name__)


class CacheMetrics:
    """缓存性能指标"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0
        self.total_time = 0.0
        self.lock = threading.Lock()
    
    @property
    def hit_rate(self) -> float:
        """缓存命中率"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def record_hit(self, duration: float = 0.0):
        """记录缓存命中"""
        with self.lock:
            self.hits += 1
            self.total_time += duration
    
    def record_miss(self, duration: float = 0.0):
        """记录缓存未命中"""
        with self.lock:
            self.misses += 1
            self.total_time += duration
    
    def record_set(self, duration: float = 0.0):
        """记录缓存设置"""
        with self.lock:
            self.sets += 1
            self.total_time += duration
    
    def record_delete(self, duration: float = 0.0):
        """记录缓存删除"""
        with self.lock:
            self.deletes += 1
            self.total_time += duration
    
    def record_error(self):
        """记录错误"""
        with self.lock:
            self.errors += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            total_ops = self.hits + self.misses + self.sets + self.deletes
            avg_time = (self.total_time / total_ops) if total_ops > 0 else 0.0
            
            return {
                'hits': self.hits,
                'misses': self.misses,
                'sets': self.sets,
                'deletes': self.deletes,
                'errors': self.errors,
                'hit_rate': self.hit_rate,
                'total_operations': total_ops,
                'average_time_ms': avg_time * 1000
            }


def performance_monitor(func):
    """性能监控装饰器"""
    
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        try:
            result = func(self, *args, **kwargs)
            duration = time.time() - start_time
            
            # 记录性能指标
            if hasattr(self, 'metrics'):
                if 'get' in func.__name__.lower():
                    if result is not None:
                        self.metrics.record_hit(duration)
                    else:
                        self.metrics.record_miss(duration)
                elif 'set' in func.__name__.lower() or 'store' in func.__name__.lower():
                    self.metrics.record_set(duration)
                elif 'delete' in func.__name__.lower():
                    self.metrics.record_delete(duration)
            
            if duration > 0.1:  # 超过100ms记录警告
                logger.warning(f"{func.__name__} 执行时间: {duration:.3f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            if hasattr(self, 'metrics'):
                self.metrics.record_error()
            logger.error(f"{func.__name__} 执行失败 ({duration:.3f}s): {e}")
            raise
    
    return wrapper


class RedisManager:
    """Redis统一管理器 - 整合session管理、缓存管理等功能"""
    
    def __init__(self):
        self._redis_client = None
        self._connection_pool = None
        self._init_redis()
        
        # 缓存配置
        self._cache_prefix = 'cache:'
        self._session_prefix = RedisConfig.REDIS_SESSION_PREFIX
        self._default_cache_ttl = 3600  # 1小时
        self._question_bank_ttl = 7200  # 题目缓存2小时
        self._tiku_list_ttl = 1800  # 题库列表缓存30分钟
        
        # 性能监控
        self.metrics = CacheMetrics()
        
        # 线程池用于并发操作
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="redis_")
        
        # 批量操作配置
        self._batch_size = 100
        self._pipeline_threshold = 5  # 超过5个操作使用pipeline
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            # 创建连接池
            self._connection_pool = redis.ConnectionPool(
                host=RedisConfig.REDIS_HOST,
                port=RedisConfig.REDIS_PORT,
                db=RedisConfig.REDIS_DB,
                password=RedisConfig.REDIS_PASSWORD,
                decode_responses=RedisConfig.REDIS_DECODE_RESPONSES,
                **RedisConfig.REDIS_POOL_CONFIG
            )
            
            # 创建Redis客户端
            self._redis_client = redis.Redis(connection_pool=self._connection_pool)
            
            # 测试连接
            self._redis_client.ping()
            logger.info("Redis连接成功")
            
        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self._redis_client = None
    
    @property
    def is_available(self) -> bool:
        """检查Redis是否可用"""
        if not self._redis_client:
            return False
        try:
            self._redis_client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis不可用: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        if not self.is_available:
            return {'status': 'unavailable', 'message': 'Redis连接不可用'}
        
        try:
            info = self._redis_client.info()
            return {
                'status': 'available',
                'redis_version': info.get('redis_version'),
                'memory_used': info.get('used_memory_human'),
                'connected_clients': info.get('connected_clients'),
                'total_commands_processed': info.get('total_commands_processed'),
                'uptime_in_seconds': info.get('uptime_in_seconds')
            }
        except Exception as e:
            return {'status': 'error', 'message': f'获取Redis信息失败: {e}'}
    
    # =========================
    # 数据序列化/反序列化
    # =========================
    
    def _serialize_data(self, data: Any) -> bytes:
        """序列化数据"""
        try:
            # 使用pickle序列化
            serialized = pickle.dumps(data)
            
            # 如果启用压缩且数据大于阈值，则压缩
            if (RedisConfig.ENABLE_COMPRESSION and 
                len(serialized) > RedisConfig.COMPRESSION_THRESHOLD):
                serialized = zlib.compress(serialized)
                # 添加压缩标记
                return b'compressed:' + serialized
            
            return serialized
            
        except Exception as e:
            logger.error(f"数据序列化失败: {e}")
            raise
    
    def _deserialize_data(self, data: bytes) -> Any:
        """反序列化数据"""
        try:
            # 检查是否有压缩标记
            if data.startswith(b'compressed:'):
                # 移除压缩标记并解压缩
                compressed_data = data[11:]  # len('compressed:') = 11
                decompressed = zlib.decompress(compressed_data)
                return pickle.loads(decompressed)
            else:
                return pickle.loads(data)
                
        except Exception as e:
            logger.error(f"数据反序列化失败: {e}")
            raise
    
    def _serialize_json(self, data: Any) -> str:
        """JSON序列化（用于缓存）"""
        return json.dumps(data, ensure_ascii=False, default=str)
    
    def _deserialize_json(self, data: str) -> Any:
        """JSON反序列化（用于缓存）"""
        return json.loads(data)
    
    # =========================
    # Session管理功能
    # =========================
    
    def _get_session_key(self, session_id: str) -> str:
        """生成Redis session key"""
        return f"{self._session_prefix}{session_id}"
    
    @performance_monitor
    def store_session_data(self, session_id: str, key: str, value: Any, 
                          ttl: Optional[int] = None) -> bool:
        """存储session数据到Redis"""
        if not self.is_available:
            return False
        
        try:
            redis_key = self._get_session_key(session_id)
            serialized_value = self._serialize_data(value)
            
            # 使用hash存储，方便单独更新某个字段
            self._redis_client.hset(redis_key, key, serialized_value)
            
            # 设置过期时间
            if ttl is None:
                ttl = RedisConfig.REDIS_SESSION_TTL
            self._redis_client.expire(redis_key, ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"存储Redis session数据失败: {e}")
            return False
    
    @performance_monitor
    def get_session_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """从Redis获取session数据"""
        if not self.is_available:
            return default
            
        try:
            redis_key = self._get_session_key(session_id)
            serialized_value = self._redis_client.hget(redis_key, key)
            
            if serialized_value is None:
                return default
            
            # 确保是bytes类型
            if isinstance(serialized_value, str):
                serialized_value = serialized_value.encode('latin-1')
            
            return self._deserialize_data(serialized_value)
            
        except Exception as e:
            logger.error(f"获取Redis session数据失败: {e}")
            return default
    
    @performance_monitor
    def delete_session_data(self, session_id: str, key: str = None) -> bool:
        """删除Redis session数据"""
        if not self.is_available:
            return False
            
        try:
            redis_key = self._get_session_key(session_id)
            
            if key is None:
                # 删除整个session
                self._redis_client.delete(redis_key)
            else:
                # 删除指定字段
                self._redis_client.hdel(redis_key, key)
            
            return True
            
        except Exception as e:
            logger.error(f"删除Redis session数据失败: {e}")
            return False
    
    @performance_monitor
    def get_all_session_data(self, session_id: str) -> Dict[str, Any]:
        """获取session的所有数据"""
        if not self.is_available:
            return {}
            
        try:
            redis_key = self._get_session_key(session_id)
            raw_data = self._redis_client.hgetall(redis_key)
            
            result = {}
            for field, serialized_value in raw_data.items():
                try:
                    # 处理字段名可能是bytes的情况
                    if isinstance(field, bytes):
                        field = field.decode('utf-8')
                    
                    # 确保值是bytes类型
                    if isinstance(serialized_value, str):
                        serialized_value = serialized_value.encode('latin-1')
                    
                    result[field] = self._deserialize_data(serialized_value)
                except Exception as e:
                    logger.warning(f"反序列化字段 {field} 失败: {e}")
                    continue
            
            return result
            
        except Exception as e:
            logger.error(f"获取Redis所有session数据失败: {e}")
            return {}
    
    @performance_monitor
    def extend_session_ttl(self, session_id: str, ttl: Optional[int] = None) -> bool:
        """延长session过期时间"""
        if not self.is_available:
            return False
            
        try:
            redis_key = self._get_session_key(session_id)
            if ttl is None:
                ttl = RedisConfig.REDIS_SESSION_TTL
            
            self._redis_client.expire(redis_key, ttl)
            return True
            
        except Exception as e:
            logger.error(f"延长Redis session过期时间失败: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """清理过期的sessions（Redis会自动清理，这里主要用于统计）"""
        if not self.is_available:
            return 0
            
        try:
            pattern = f"{self._session_prefix}*"
            keys = self._redis_client.keys(pattern)
            
            expired_count = 0
            for key in keys:
                ttl = self._redis_client.ttl(key)
                if ttl == -2:  # key不存在（已过期）
                    expired_count += 1
            
            return expired_count
            
        except Exception as e:
            logger.error(f"清理过期sessions失败: {e}")
            return 0
    
    # =========================
    # 缓存管理功能
    # =========================
    
    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self._cache_prefix}{key}"
    
    @performance_monitor
    def cache_get(self, key: str, default=None) -> Any:
        """从缓存获取数据"""
        if not self.is_available:
            return default
        
        try:
            redis_key = self._get_cache_key(key)
            data = self._redis_client.get(redis_key)
            if data is None:
                return default
            return self._deserialize_json(data)
        except Exception as e:
            logger.error(f"从Redis缓存获取数据失败 {key}: {e}")
            return default
    
    @performance_monitor
    def cache_set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        if not self.is_available:
            return False
        
        try:
            redis_key = self._get_cache_key(key)
            data = self._serialize_json(value)
            if ttl is None:
                ttl = self._default_cache_ttl
            self._redis_client.setex(redis_key, ttl, data)
            return True
        except Exception as e:
            logger.error(f"设置Redis缓存失败 {key}: {e}")
            return False
    
    @performance_monitor
    def cache_delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self.is_available:
            return False
        
        try:
            redis_key = self._get_cache_key(key)
            self._redis_client.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"删除Redis缓存失败 {key}: {e}")
            return False
    
    def cache_exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        if not self.is_available:
            return False
        
        try:
            redis_key = self._get_cache_key(key)
            return bool(self._redis_client.exists(redis_key))
        except Exception as e:
            logger.error(f"检查Redis缓存存在性失败 {key}: {e}")
            return False
    
    def cache_ttl(self, key: str) -> int:
        """获取缓存过期时间"""
        if not self.is_available:
            return -1
        
        try:
            redis_key = self._get_cache_key(key)
            return self._redis_client.ttl(redis_key)
        except Exception as e:
            logger.error(f"获取Redis缓存TTL失败 {key}: {e}")
            return -1
    
    # =========================
    # 批量操作
    # =========================
    
    @performance_monitor
    def cache_mget(self, keys: List[str]) -> Dict[str, Any]:
        """批量获取缓存数据"""
        if not self.is_available or not keys:
            return {}
        
        try:
            redis_keys = [self._get_cache_key(key) for key in keys]
            values = self._redis_client.mget(redis_keys)
            
            result = {}
            for i, (key, value) in enumerate(zip(keys, values)):
                if value is not None:
                    try:
                        result[key] = self._deserialize_json(value)
                    except Exception as e:
                        logger.warning(f"反序列化缓存数据失败 {key}: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"批量获取Redis缓存失败: {e}")
            return {}
    
    @performance_monitor
    def cache_mset(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存数据"""
        if not self.is_available or not data:
            return False
        
        try:
            if ttl is None:
                ttl = self._default_cache_ttl
            
            # 使用pipeline提高性能
            with self._redis_client.pipeline() as pipe:
                for key, value in data.items():
                    redis_key = self._get_cache_key(key)
                    serialized_value = self._serialize_json(value)
                    pipe.setex(redis_key, ttl, serialized_value)
                
                pipe.execute()
            
            return True
            
        except Exception as e:
            logger.error(f"批量设置Redis缓存失败: {e}")
            return False
    
    @performance_monitor
    def cache_delete_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        if not self.is_available:
            return 0
        
        try:
            redis_pattern = self._get_cache_key(pattern)
            keys = self._redis_client.keys(redis_pattern)
            if keys:
                self._redis_client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            logger.error(f"按模式删除Redis缓存失败 {pattern}: {e}")
            return 0
    
    # =========================
    # 特定业务缓存接口
    # =========================
    
    def get_tiku_list_cache(self) -> Optional[Dict[str, Any]]:
        """获取题库列表缓存"""
        return self.cache_get('tiku_list')
    
    def set_tiku_list_cache(self, data: Dict[str, Any]) -> bool:
        """设置题库列表缓存"""
        return self.cache_set('tiku_list', data, self._tiku_list_ttl)
    
    def get_file_options_cache(self) -> Optional[Dict[str, Any]]:
        """获取文件选项缓存"""
        return self.cache_get('file_options')
    
    def set_file_options_cache(self, data: Dict[str, Any]) -> bool:
        """设置文件选项缓存"""
        return self.cache_set('file_options', data, self._tiku_list_ttl)
    
    def get_question_bank_cache(self, tiku_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取题库题目缓存"""
        return self.cache_get(f'question_bank_{tiku_id}')
    
    def set_question_bank_cache(self, tiku_id: int, data: List[Dict[str, Any]]) -> bool:
        """设置题库题目缓存"""
        return self.cache_set(f'question_bank_{tiku_id}', data, self._question_bank_ttl)
    
    def clear_all_question_bank_cache(self) -> int:
        """清除所有题库题目缓存"""
        return self.cache_delete_pattern('question_bank_*')
    
    # =========================
    # 缓存管理和监控
    # =========================
    
    def refresh_all_cache(self) -> Dict[str, Any]:
        """刷新所有缓存"""
        logger.info("开始刷新所有Redis缓存")
        
        try:
            if not self.is_available:
                return {
                    'success': False,
                    'message': 'Redis不可用，无法刷新缓存',
                    'cleared_keys': 0
                }
            
            # 删除所有缓存
            cache_keys = ['tiku_list', 'file_options']
            cleared_count = 0
            
            for key in cache_keys:
                if self.cache_delete(key):
                    cleared_count += 1
            
            # 删除所有题目缓存
            question_cache_count = self.clear_all_question_bank_cache()
            cleared_count += question_cache_count
            
            logger.info(f"成功刷新Redis缓存，清除了 {cleared_count} 个键")
            
            return {
                'success': True,
                'message': 'Redis缓存刷新成功',
                'cleared_keys': cleared_count
            }
            
        except Exception as e:
            logger.error(f"刷新Redis缓存失败: {e}")
            return {
                'success': False,
                'message': f'刷新缓存失败: {str(e)}',
                'cleared_keys': 0
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = self.metrics.get_stats()
        
        if self.is_available:
            try:
                # 获取Redis内存信息
                info = self._redis_client.info('memory')
                stats.update({
                    'redis_memory_used': info.get('used_memory_human'),
                    'redis_memory_peak': info.get('used_memory_peak_human'),
                    'redis_memory_rss': info.get('used_memory_rss_human')
                })
                
                # 获取缓存键统计
                cache_pattern = self._get_cache_key('*')
                session_pattern = self._get_session_key('*')
                
                cache_keys = len(self._redis_client.keys(cache_pattern))
                session_keys = len(self._redis_client.keys(session_pattern))
                
                stats.update({
                    'cache_keys_count': cache_keys,
                    'session_keys_count': session_keys,
                    'total_keys': cache_keys + session_keys
                })
                
            except Exception as e:
                logger.error(f"获取Redis统计信息失败: {e}")
                stats['redis_error'] = str(e)
        
        stats['redis_available'] = self.is_available
        return stats
    
    # =========================
    # 资源清理
    # =========================
    
    def cleanup(self):
        """清理资源"""
        try:
            if self._executor:
                self._executor.shutdown(wait=True)
            
            if self._connection_pool:
                self._connection_pool.disconnect()
            
            logger.info("Redis管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"Redis管理器资源清理失败: {e}")
    
    def __del__(self):
        """析构函数"""
        self.cleanup()


# 全局Redis管理器实例
redis_manager = RedisManager()

# 需要存储在Redis中的session keys - 大数据量的keys
REDIS_STORED_KEYS: Set[str] = {
    SESSION_KEYS['QUESTION_INDICES'],
    SESSION_KEYS['WRONG_INDICES'],
    SESSION_KEYS['QUESTION_STATUSES'],
    SESSION_KEYS['ANSWER_HISTORY']
}


# =========================
# 高级接口函数
# =========================

def get_hybrid_session_value(key: str, default: Any = None) -> Any:
    """
    混合session值获取 - 大数据从Redis获取，小数据从cookie获取
    如果Redis不可用，回退到数据库存储
    """
    # 如果是大数据key，优先从Redis获取
    if key in REDIS_STORED_KEYS:
        session_id = session.get('session_id')
        logger.debug(f"混合获取key {key}: session_id={'有' if session_id else '无'}, redis_available={redis_manager.is_available}")
        
        if session_id and redis_manager.is_available:
            redis_value = redis_manager.get_session_data(session_id, key)
            logger.debug(f"Redis获取key {key}: {'有值' if redis_value is not None else '无值'}")
            if redis_value is not None:
                return redis_value
        
        # Redis不可用时回退到数据库
        try:
            from .session_manager import get_database_session_value
            db_value = get_database_session_value(key, default)
            logger.debug(f"数据库回退获取key {key}: {'有值' if db_value != default else '无值/默认值'}")
            return db_value
        except ImportError:
            logger.warning("无法导入数据库session函数，返回默认值")
            return default
    
    # 小数据从cookie获取
    cookie_value = session.get(key, default)
    logger.debug(f"Cookie获取key {key}: {'有值' if cookie_value != default else '无值/默认值'}")
    return cookie_value


def set_hybrid_session_value(key: str, value: Any) -> None:
    """
    混合session值设置 - 大数据存储在Redis，小数据存储在cookie
    """
    # 如果是大数据key，存储到Redis
    if key in REDIS_STORED_KEYS:
        session_id = session.get('session_id')
        if not session_id:
            # 生成新的session ID
            import uuid
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
            session.modified = True
            logger.debug(f"生成新的session_id: {session_id}")
        
        logger.debug(f"混合设置key {key}: session_id={session_id}, redis_available={redis_manager.is_available}")
        
        if redis_manager.is_available:
            success = redis_manager.store_session_data(session_id, key, value)
            logger.debug(f"Redis存储key {key}: {'成功' if success else '失败'}")
            if success:
                return
        
        # Redis存储失败时回退到数据库
        try:
            from .session_manager import set_database_session_value
            logger.debug(f"回退到数据库存储key {key}")
            set_database_session_value(key, value)
            return
        except ImportError:
            logger.warning("无法导入数据库session函数，数据可能丢失")
    
    # 小数据存储在cookie
    logger.debug(f"设置小数据key {key} 到cookie")
    session[key] = value
    session.modified = True
