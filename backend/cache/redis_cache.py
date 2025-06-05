"""
高性能Redis缓存管理器
支持批量操作、管道、异步等特性
"""
import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
import threading

from ..RedisManager import RedisManager
from ..models import Question, QuestionBank, TikuInfo

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

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        with self.lock:
            return {
                'hits': self.hits,
                'misses': self.misses,
                'sets': self.sets,
                'deletes': self.deletes,
                'errors': self.errors,
                'hit_rate': round(self.hit_rate, 2),
                'avg_time_ms': round(self.total_time * 1000 / max(1, self.hits + self.misses), 2)
            }


def measure_time(metrics: CacheMetrics, operation: str):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                if operation == 'get':
                    if result is not None:
                        metrics.record_hit(duration)
                    else:
                        metrics.record_miss(duration)
                elif operation == 'set':
                    metrics.record_set(duration)
                elif operation == 'delete':
                    metrics.record_delete(duration)
                
                return result
            except Exception as e:
                metrics.record_error()
                logger.error(f"Cache operation {operation} failed: {e}")
                raise
        return wrapper
    return decorator


class RedisCacheManager:
    """高性能Redis缓存管理器"""
    
    def __init__(self, redis_manager: Optional[RedisManager] = None):
        self.redis_manager = redis_manager or RedisManager()
        self._cache_prefix = 'cache:'
        self._default_ttl = 3600  # 1小时
        self._question_bank_ttl = 7200  # 题目缓存2小时
        self._tiku_list_ttl = 1800  # 题库列表缓存30分钟
        self.metrics = CacheMetrics()
        
        # 线程池用于并发操作
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="cache_")
        
        # 批量操作配置
        self._batch_size = 100
        self._pipeline_threshold = 5  # 超过5个操作使用pipeline

    def _get_cache_key(self, key: str) -> str:
        """生成缓存键"""
        return f"{self._cache_prefix}{key}"

    def _is_available(self) -> bool:
        """检查Redis是否可用"""
        return self.redis_manager.is_available

    def _serialize_data(self, data: Any) -> str:
        """序列化数据"""
        if isinstance(data, (Question, QuestionBank, TikuInfo)):
            # 对于数据类对象，转换为字典
            if hasattr(data, 'to_dict'):
                return json.dumps(data.to_dict(), ensure_ascii=False)
            elif hasattr(data, '__dict__'):
                return json.dumps(data.__dict__, ensure_ascii=False)
        
        return json.dumps(data, ensure_ascii=False, default=str)

    def _deserialize_data(self, data: str, data_type: Optional[type] = None) -> Any:
        """反序列化数据"""
        try:
            parsed_data = json.loads(data)
            
            # 如果指定了数据类型，尝试转换
            if data_type and hasattr(data_type, 'from_dict'):
                return data_type.from_dict(parsed_data)
            
            return parsed_data
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to deserialize data: {e}")
            return None

    @measure_time(lambda self: self.metrics, 'get')
    def get(self, key: str, default: Any = None, data_type: Optional[type] = None) -> Any:
        """获取缓存数据"""
        if not self._is_available():
            return default

        try:
            redis_key = self._get_cache_key(key)
            data = self.redis_manager._redis_client.get(redis_key)
            
            if data is None:
                return default
            
            return self._deserialize_data(data, data_type)
        
        except Exception as e:
            logger.error(f"Get cache failed for key {key}: {e}")
            return default

    @measure_time(lambda self: self.metrics, 'set')
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        if not self._is_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            data = self._serialize_data(value)
            cache_ttl = ttl or self._default_ttl
            
            self.redis_manager._redis_client.setex(redis_key, cache_ttl, data)
            return True
        
        except Exception as e:
            logger.error(f"Set cache failed for key {key}: {e}")
            return False

    @measure_time(lambda self: self.metrics, 'delete')
    def delete(self, key: str) -> bool:
        """删除缓存数据"""
        if not self._is_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            result = self.redis_manager._redis_client.delete(redis_key)
            return result > 0
        
        except Exception as e:
            logger.error(f"Delete cache failed for key {key}: {e}")
            return False

    def mget(self, keys: List[str], data_type: Optional[type] = None) -> Dict[str, Any]:
        """批量获取缓存数据"""
        if not self._is_available() or not keys:
            return {}

        try:
            redis_keys = [self._get_cache_key(key) for key in keys]
            values = self.redis_manager._redis_client.mget(redis_keys)
            
            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    self.metrics.record_hit()
                    result[key] = self._deserialize_data(value, data_type)
                else:
                    self.metrics.record_miss()
            
            return result
        
        except Exception as e:
            logger.error(f"Batch get cache failed: {e}")
            self.metrics.record_error()
            return {}

    def mset(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """批量设置缓存数据"""
        if not self._is_available() or not data:
            return False

        try:
            cache_ttl = ttl or self._default_ttl
            
            # 使用pipeline提升性能
            pipe = self.redis_manager._redis_client.pipeline()
            
            for key, value in data.items():
                redis_key = self._get_cache_key(key)
                serialized_value = self._serialize_data(value)
                pipe.setex(redis_key, cache_ttl, serialized_value)
            
            pipe.execute()
            self.metrics.record_set()
            return True
        
        except Exception as e:
            logger.error(f"Batch set cache failed: {e}")
            self.metrics.record_error()
            return False

    def delete_pattern(self, pattern: str) -> int:
        """根据模式删除缓存"""
        if not self._is_available():
            return 0

        try:
            full_pattern = self._get_cache_key(pattern)
            keys = self.redis_manager._redis_client.keys(full_pattern)
            
            if not keys:
                return 0
            
            # 分批删除避免阻塞
            deleted_count = 0
            for i in range(0, len(keys), self._batch_size):
                batch_keys = keys[i:i + self._batch_size]
                deleted_count += self.redis_manager._redis_client.delete(*batch_keys)
            
            self.metrics.record_delete()
            return deleted_count
        
        except Exception as e:
            logger.error(f"Delete pattern cache failed for pattern {pattern}: {e}")
            self.metrics.record_error()
            return 0

    def exists(self, key: str) -> bool:
        """检查缓存键是否存在"""
        if not self._is_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            return bool(self.redis_manager._redis_client.exists(redis_key))
        
        except Exception as e:
            logger.error(f"Check cache existence failed for key {key}: {e}")
            return False

    def expire(self, key: str, ttl: int) -> bool:
        """设置缓存过期时间"""
        if not self._is_available():
            return False

        try:
            redis_key = self._get_cache_key(key)
            return bool(self.redis_manager._redis_client.expire(redis_key, ttl))
        
        except Exception as e:
            logger.error(f"Set cache expiration failed for key {key}: {e}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """获取缓存剩余生存时间"""
        if not self._is_available():
            return None

        try:
            redis_key = self._get_cache_key(key)
            ttl = self.redis_manager._redis_client.ttl(redis_key)
            return ttl if ttl > 0 else None
        
        except Exception as e:
            logger.error(f"Get cache TTL failed for key {key}: {e}")
            return None

    # 业务特定的缓存方法
    def get_tiku_list(self) -> Optional[Dict[str, Any]]:
        """获取题库列表缓存"""
        return self.get('tiku_list', data_type=None)

    def set_tiku_list(self, data: Dict[str, Any]) -> bool:
        """设置题库列表缓存"""
        return self.set('tiku_list', data, ttl=self._tiku_list_ttl)

    def get_file_options(self) -> Optional[Dict[str, Any]]:
        """获取文件选项缓存"""
        return self.get('file_options', data_type=None)

    def set_file_options(self, data: Dict[str, Any]) -> bool:
        """设置文件选项缓存"""
        return self.set('file_options', data, ttl=self._tiku_list_ttl)

    def get_question_bank(self, tiku_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取题库题目缓存"""
        return self.get(f'question_bank_{tiku_id}', data_type=None)

    def set_question_bank(self, tiku_id: int, questions: List[Dict[str, Any]]) -> bool:
        """设置题库题目缓存"""
        return self.set(f'question_bank_{tiku_id}', questions, ttl=self._question_bank_ttl)

    def invalidate_tiku_cache(self) -> int:
        """失效题库相关缓存"""
        patterns = ['tiku_list', 'file_options', 'question_bank_*']
        total_deleted = 0
        
        for pattern in patterns:
            deleted = self.delete_pattern(pattern)
            total_deleted += deleted
            logger.info(f"Invalidated {deleted} cache entries for pattern: {pattern}")
        
        return total_deleted

    def warm_up_cache(self, tiku_ids: List[int]) -> Dict[str, bool]:
        """预热指定题库的缓存"""
        results = {}
        
        # 这里需要与数据访问层协作，暂时返回占位符
        for tiku_id in tiku_ids:
            # 实际实现中，这里会调用数据库加载题目并缓存
            results[f'question_bank_{tiku_id}'] = True
        
        return results

    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        try:
            info = self.redis_manager._redis_client.info('memory')
            
            return {
                'is_available': self._is_available(),
                'memory_usage': {
                    'used_memory': info.get('used_memory_human'),
                    'used_memory_peak': info.get('used_memory_peak_human'),
                    'used_memory_rss': info.get('used_memory_rss_human')
                },
                'metrics': self.metrics.to_dict(),
                'configuration': {
                    'default_ttl': self._default_ttl,
                    'question_bank_ttl': self._question_bank_ttl,
                    'tiku_list_ttl': self._tiku_list_ttl,
                    'batch_size': self._batch_size
                }
            }
        
        except Exception as e:
            logger.error(f"Get cache info failed: {e}")
            return {
                'is_available': False,
                'error': str(e),
                'metrics': self.metrics.to_dict()
            }

    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False) 