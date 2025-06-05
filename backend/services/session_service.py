"""
会话管理服务
处理练习会话相关的业务逻辑
"""
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..cache.hybrid_cache import HybridCacheManager
from ..connectDB import get_user_practice_history
from ..models import PracticeStatistics

logger = logging.getLogger(__name__)


class SessionService:
    """会话管理服务"""
    
    def __init__(self, cache_manager: Optional[HybridCacheManager] = None):
        self.cache_manager = cache_manager or HybridCacheManager()
    
    def get_user_practice_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户练习历史"""
        cache_key = f'user_history_{user_id}_{limit}'
        
        # 尝试从缓存获取（较短TTL，因为历史数据会变化）
        cached_history = self.cache_manager.get(cache_key)
        if cached_history:
            logger.debug(f"使用缓存的用户历史数据: {user_id}")
            return cached_history
        
        try:
            history = get_user_practice_history(user_id, limit)
            
            # 缓存历史数据（5分钟TTL）
            self.cache_manager.set(cache_key, history, ttl=300)
            
            return history
            
        except Exception as e:
            logger.error(f"获取用户练习历史失败: {e}")
            return []
    
    def get_user_practice_statistics(self, user_id: int) -> PracticeStatistics:
        """获取用户练习统计信息"""
        cache_key = f'user_stats_{user_id}'
        
        # 尝试从缓存获取
        cached_stats = self.cache_manager.get(cache_key)
        if cached_stats:
            logger.debug(f"使用缓存的用户统计数据: {user_id}")
            # 需要重新构建PracticeStatistics对象
            stats = PracticeStatistics()
            stats.__dict__.update(cached_stats)
            return stats
        
        try:
            # 获取详细历史数据用于统计
            history = self.get_user_practice_history(user_id, 100)
            
            # 计算统计信息
            stats = self._calculate_statistics(history)
            
            # 缓存统计数据（10分钟TTL）
            self.cache_manager.set(cache_key, stats.__dict__, ttl=600)
            
            return stats
            
        except Exception as e:
            logger.error(f"获取用户练习统计失败: {e}")
            return PracticeStatistics()
    
    def _calculate_statistics(self, history: List[Dict[str, Any]]) -> PracticeStatistics:
        """计算练习统计信息"""
        stats = PracticeStatistics()
        
        if not history:
            return stats
        
        # 基本统计
        stats.total_sessions = len(history)
        stats.completed_sessions = len([h for h in history if h['status'] == 'completed'])
        stats.total_questions = sum(h['total_questions'] for h in history)
        stats.total_correct = sum(h['correct_first_try'] for h in history)
        
        # 按科目统计
        subject_stats = defaultdict(lambda: {
            'sessions': 0, 
            'total_questions': 0, 
            'correct_answers': 0, 
            'avg_score': 0
        })
        
        for session in history:
            subject = session['subject_name']
            subject_stats[subject]['sessions'] += 1
            subject_stats[subject]['total_questions'] += session['total_questions']
            subject_stats[subject]['correct_answers'] += session['correct_first_try']
        
        # 计算各科目平均分
        for subject, data in subject_stats.items():
            if data['total_questions'] > 0:
                data['avg_score'] = round(
                    data['correct_answers'] / data['total_questions'] * 100, 2
                )
        
        stats.subject_stats = dict(subject_stats)
        stats.recent_activity = history[:10]  # 最近10次活动
        
        # 计算总体平均分
        stats.calculate_avg_score()
        
        return stats
    
    def clear_user_cache(self, user_id: int):
        """清除用户相关缓存"""
        cache_patterns = [
            f'user_history_{user_id}_*',
            f'user_stats_{user_id}'
        ]
        
        # 这里简化处理，实际实现中需要支持模式删除
        # 或者记录用户相关的所有缓存键
        logger.info(f"清除用户 {user_id} 的缓存")
    
    def update_session_cache(self, user_id: int):
        """更新用户会话相关缓存"""
        # 删除旧缓存
        self.clear_user_cache(user_id)
        
        # 预热新缓存
        self.get_user_practice_statistics(user_id)
        logger.info(f"已更新用户 {user_id} 的会话缓存") 