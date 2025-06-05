"""
Redis Session 管理模块
用于将session的一部分数据存储在Redis中，减少cookie大小并提高性能
"""
import json
import logging
import pickle
import zlib
from typing import Any, Optional, Dict, Set
from datetime import timedelta
import redis
from flask import session
from .config import RedisConfig, SESSION_KEYS

logger = logging.getLogger(__name__)


class RedisSessionManager:
    """Redis Session管理器"""
    
    def __init__(self):
        self._redis_client = None
        self._connection_pool = None
        self._init_redis()
    
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
    
    def _get_session_key(self, session_id: str) -> str:
        """生成Redis session key"""
        return f"{RedisConfig.REDIS_SESSION_PREFIX}{session_id}"
    
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
            pattern = f"{RedisConfig.REDIS_SESSION_PREFIX}*"
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


# 全局Redis session管理器实例
redis_session_manager = RedisSessionManager()


# 需要存储在Redis中的session keys - 大数据量的keys
REDIS_STORED_KEYS: Set[str] = {
    SESSION_KEYS['QUESTION_INDICES'],
    SESSION_KEYS['WRONG_INDICES'], 
    SESSION_KEYS['QUESTION_STATUSES'],
    SESSION_KEYS['ANSWER_HISTORY']
}

# 优化的session数据访问接口
def get_hybrid_session_value(key: str, default: Any = None) -> Any:
    """
    混合session值获取 - 大数据从Redis获取，小数据从cookie获取
    如果Redis不可用，回退到数据库存储
    """
    # 如果是大数据key，优先从Redis获取
    if key in REDIS_STORED_KEYS:
        session_id = session.get('session_id')
        if session_id and redis_session_manager.is_available:
            redis_value = redis_session_manager.get_session_data(session_id, key)
            if redis_value is not None:
                return redis_value
        
        # Redis不可用时回退到数据库
        from .session_manager import get_database_session_value
        return get_database_session_value(key, default)
    
    # 小数据从cookie获取
    return session.get(key, default)


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
        
        if redis_session_manager.is_available:
            success = redis_session_manager.store_session_data(session_id, key, value)
            if success:
                return
        
        # Redis存储失败时回退到数据库
        from .session_manager import set_database_session_value
        set_database_session_value(key, value)
        return
    
    # 小数据存储在cookie
    session[key] = value
    session.modified = True 