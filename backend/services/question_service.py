"""
题目管理服务
处理题目相关的业务逻辑
"""
import logging
from typing import Dict, List, Optional, Any

from ..cache.hybrid_cache import HybridCacheManager
from ..connectDB import get_question_by_db_id
from ..utils import format_answer_display

logger = logging.getLogger(__name__)


class QuestionService:
    """题目管理服务"""
    
    def __init__(self, cache_manager: Optional[HybridCacheManager] = None):
        self.cache_manager = cache_manager or HybridCacheManager()
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取题目详情"""
        if not question_id.startswith('db_'):
            return None
        
        try:
            db_id = int(question_id.replace('db_', ''))
        except ValueError:
            return None
        
        # 尝试从缓存获取
        cache_key = f'question_detail_{db_id}'
        cached_question = self.cache_manager.get(cache_key)
        
        if cached_question:
            logger.debug(f"使用缓存的题目数据: {question_id}")
            return cached_question
        
        # 从数据库获取
        question_data = get_question_by_db_id(db_id)
        if not question_data:
            return None
        
        # 添加格式化的答案显示
        self._add_formatted_answer(question_data)
        
        # 缓存题目数据（较短TTL，因为题目可能更新）
        self.cache_manager.set(cache_key, question_data, ttl=1800)  # 30分钟
        
        return question_data
    
    def _add_formatted_answer(self, question_data: Dict[str, Any]):
        """添加格式化的答案显示"""
        options = question_data.get('options_for_practice', {})
        is_multiple_choice = question_data.get('is_multiple_choice', False)
        correct_answer = question_data.get('answer', '').upper()
        
        question_data['correct_answer_display'] = format_answer_display(
            correct_answer, options, is_multiple_choice
        )
    
    def get_question_analysis(self, question_id: str) -> Optional[Dict[str, Any]]:
        """获取题目解析"""
        question_data = self.get_question_by_id(question_id)
        if not question_data:
            return None
        
        return {
            'analysis': question_data.get('explanation', '暂无解析'),
            'knowledge_points': question_data.get('knowledge_points', [])
        }
    
    def batch_get_questions(self, question_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取题目"""
        results = {}
        
        for question_id in question_ids:
            results[question_id] = self.get_question_by_id(question_id)
        
        return results 