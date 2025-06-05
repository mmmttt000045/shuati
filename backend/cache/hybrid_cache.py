"""
混合缓存管理器
结合内存缓存和Redis缓存，提供最佳性能
"""
import logging
import time
from typing import Dict, List, Optional, Any
from .redis_cache import RedisCacheManager
from functools import lru_cache

logger = logging.getLogger(__name__)


class HybridCacheManager:
    """混合缓存管理器"""
    
    def __init__(self, redis_manager=None):
        self.redis_cache = RedisCacheManager(redis_manager)
        self._local_cache_size = 1000  # 本地缓存最大条目数
        self._local_cache = {}  # 简单的本地内存缓存
        self._local_cache_access_times = {}  # 访问时间记录
        
    def _evict_local_cache(self):
        """LRU淘汰本地缓存"""
        if len(self._local_cache) >= self._local_cache_size:
            # 找到最久未访问的键
            oldest_key = min(self._local_cache_access_times.keys(), 
                           key=self._local_cache_access_times.get)
            del self._local_cache[oldest_key]
            del self._local_cache_access_times[oldest_key]
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存数据（优先本地缓存）"""
        # 先检查本地缓存
        if key in self._local_cache:
            self._local_cache_access_times[key] = time.time()
            return self._local_cache[key]
        
        # 从Redis获取
        value = self.redis_cache.get(key, default)
        
        # 如果从Redis获取到数据，存入本地缓存
        if value is not default:
            self._evict_local_cache()
            self._local_cache[key] = value
            self._local_cache_access_times[key] = time.time()
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存数据"""
        # 同时设置本地缓存和Redis缓存
        self._evict_local_cache()
        self._local_cache[key] = value
        self._local_cache_access_times[key] = time.time()
        
        return self.redis_cache.set(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """删除缓存数据"""
        # 同时删除本地缓存和Redis缓存
        if key in self._local_cache:
            del self._local_cache[key]
            del self._local_cache_access_times[key]
        
        return self.redis_cache.delete(key)
    
    def clear_local_cache(self):
        """清空本地缓存"""
        self._local_cache.clear()
        self._local_cache_access_times.clear()
    
    # 业务专用方法
    def get_tiku_list(self) -> Optional[Dict[str, Any]]:
        """获取题库列表（使用混合缓存）"""
        return self.get('tiku_list')
    
    def set_tiku_list(self, data: Dict[str, Any]) -> bool:
        """设置题库列表缓存"""
        return self.set('tiku_list', data, ttl=1800)
    
    def get_file_options(self) -> Optional[Dict[str, Any]]:
        """获取文件选项（使用混合缓存）"""
        return self.get('file_options')
    
    def set_file_options(self, data: Dict[str, Any]) -> bool:
        """设置文件选项缓存"""
        return self.set('file_options', data, ttl=1800)
    
    def get_question_bank(self, tiku_id: int) -> Optional[List[Dict[str, Any]]]:
        """获取题库题目（使用混合缓存）"""
        return self.get(f'question_bank_{tiku_id}')
    
    def set_question_bank(self, tiku_id: int, questions: List[Dict[str, Any]]) -> bool:
        """设置题库题目缓存"""
        return self.set(f'question_bank_{tiku_id}', questions, ttl=7200)
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        redis_info = self.redis_cache.get_cache_info()
        
        return {
            'redis': redis_info,
            'local': {
                'entries': len(self._local_cache),
                'max_size': self._local_cache_size,
                'hit_rate': 'N/A'  # 可以在未来实现
            }
        } 