"""
内存缓存管理器
提供高速的本地内存缓存功能
"""
import logging
import time
import threading
from typing import Dict, Any, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)


class MemoryCacheManager:
    """内存缓存管理器 - LRU策略"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._expiry_times = {}
        self._lock = threading.RLock()
        
        # 统计信息
        self._hits = 0
        self._misses = 0
        self._sets = 0
        self._evictions = 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default
            
            # 检查是否过期
            if self._is_expired(key):
                self._remove_key(key)
                self._misses += 1
                return default
            
            # 移动到末尾（LRU）
            value = self._cache.pop(key)
            self._cache[key] = value
            
            self._hits += 1
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self._lock:
            cache_ttl = ttl or self.default_ttl
            expiry_time = time.time() + cache_ttl
            
            # 如果键已存在，更新值和过期时间
            if key in self._cache:
                self._cache.pop(key)  # 移除旧值
            
            # 检查是否需要清理空间
            self._evict_if_needed()
            
            # 添加新值
            self._cache[key] = value
            self._expiry_times[key] = expiry_time
            
            self._sets += 1
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        with self._lock:
            if key in self._cache:
                self._remove_key(key)
                return True
            return False
    
    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._cache.clear()
            self._expiry_times.clear()
            logger.info("内存缓存已清空")
    
    def _is_expired(self, key: str) -> bool:
        """检查键是否过期"""
        expiry_time = self._expiry_times.get(key)
        if expiry_time is None:
            return True
        return time.time() > expiry_time
    
    def _remove_key(self, key: str):
        """移除键及其过期时间"""
        self._cache.pop(key, None)
        self._expiry_times.pop(key, None)
    
    def _evict_if_needed(self):
        """如果需要，清理过期和多余的缓存"""
        # 清理过期项
        expired_keys = [
            key for key in self._cache 
            if self._is_expired(key)
        ]
        
        for key in expired_keys:
            self._remove_key(key)
            self._evictions += 1
        
        # 如果仍然超过最大容量，移除最旧的项
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._remove_key(oldest_key)
            self._evictions += 1
    
    def cleanup_expired(self):
        """主动清理过期项"""
        with self._lock:
            expired_keys = [
                key for key in self._cache 
                if self._is_expired(key)
            ]
            
            for key in expired_keys:
                self._remove_key(key)
            
            if expired_keys:
                logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hits': self._hits,
                'misses': self._misses,
                'sets': self._sets,
                'evictions': self._evictions,
                'hit_rate': round(hit_rate, 2),
                'current_size': len(self._cache),
                'max_size': self.max_size,
                'memory_usage_percent': round(len(self._cache) / self.max_size * 100, 2)
            }
    
    def get_info(self) -> Dict[str, Any]:
        """获取缓存详细信息"""
        stats = self.get_stats()
        
        with self._lock:
            # 获取即将过期的键数量
            current_time = time.time()
            expiring_soon = sum(
                1 for expiry_time in self._expiry_times.values()
                if 0 < expiry_time - current_time < 60  # 1分钟内过期
            )
            
            stats.update({
                'expiring_soon_count': expiring_soon,
                'avg_ttl_remaining': self._calculate_avg_ttl_remaining(),
                'oldest_entry_age': self._get_oldest_entry_age()
            })
        
        return stats
    
    def _calculate_avg_ttl_remaining(self) -> float:
        """计算平均剩余TTL"""
        if not self._expiry_times:
            return 0.0
        
        current_time = time.time()
        total_ttl = sum(
            max(0, expiry_time - current_time)
            for expiry_time in self._expiry_times.values()
        )
        
        return round(total_ttl / len(self._expiry_times), 2)
    
    def _get_oldest_entry_age(self) -> float:
        """获取最旧条目的年龄（秒）"""
        if not self._expiry_times:
            return 0.0
        
        current_time = time.time()
        oldest_expiry = min(self._expiry_times.values())
        
        # 假设TTL是默认值来估算年龄
        estimated_creation_time = oldest_expiry - self.default_ttl
        return round(current_time - estimated_creation_time, 2)
    
    def __len__(self) -> int:
        """返回当前缓存项数量"""
        return len(self._cache)
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在且未过期"""
        with self._lock:
            if key not in self._cache:
                return False
            
            if self._is_expired(key):
                self._remove_key(key)
                return False
            
            return True 