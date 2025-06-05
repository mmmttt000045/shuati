"""
高性能练习服务
处理练习核心业务逻辑
"""
import logging
import random
import time
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from ..cache.hybrid_cache import HybridCacheManager
from ..models import Question, QuestionBank, QuestionType, classify_question_type, get_question_type_name
from ..connectDB import get_questions_by_tiku, get_question_by_db_id
from ..utils import validate_answer, format_answer_display

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """性能跟踪器"""
    def __init__(self):
        self.operation_times = defaultdict(list)
    
    def track(self, operation: str, duration: float):
        """记录操作时间"""
        self.operation_times[operation].append(duration)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = {}
        for operation, times in self.operation_times.items():
            stats[operation] = {
                'count': len(times),
                'total_time': sum(times),
                'avg_time': sum(times) / len(times) if times else 0,
                'max_time': max(times) if times else 0
            }
        return stats


class QuestionGenerator:
    """高性能题目生成器"""
    
    def __init__(self):
        self.performance_tracker = PerformanceTracker()
    
    def generate_question_indices(self, question_bank: List[dict], 
                                selected_types: Optional[List[str]] = None,
                                shuffle_enabled: bool = True) -> List[int]:
        """
        高性能题目索引生成
        使用预索引和批量操作
        """
        start_time = time.time()
        
        if not question_bank:
            return []
        
        try:
            # 将字符串类型转换为枚举类型
            target_types = []
            if selected_types:
                type_mapping = {
                    'single_choice': QuestionType.SINGLE_CHOICE,
                    'multiple_choice': QuestionType.MULTIPLE_CHOICE,
                    'judgment': QuestionType.JUDGMENT,
                    'other': QuestionType.OTHER
                }
                target_types = [type_mapping.get(t) for t in selected_types if t in type_mapping]
            else:
                target_types = [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, 
                              QuestionType.JUDGMENT, QuestionType.OTHER]
            
            # 预分配索引字典，避免动态扩容
            indices_by_type = {
                QuestionType.SINGLE_CHOICE: [],
                QuestionType.MULTIPLE_CHOICE: [],
                QuestionType.JUDGMENT: [],
                QuestionType.OTHER: []
            }
            
            # 单次遍历分类（向量化操作）
            for i, question in enumerate(question_bank):
                question_type = classify_question_type(
                    question.get('type', ''),
                    question.get('is_multiple_choice', False)
                )
                indices_by_type[question_type].append(i)
            
            # 批量打乱（如果需要）
            if shuffle_enabled:
                for indices_list in indices_by_type.values():
                    if indices_list:
                        random.shuffle(indices_list)
            
            # 组合结果
            result_indices = []
            summary_parts = []
            
            for q_type in target_types:
                indices = indices_by_type[q_type]
                result_indices.extend(indices)
                if indices:
                    type_name = get_question_type_name(q_type)
                    summary_parts.append(f"{type_name} {len(indices)} 道")
            
            # 性能记录
            duration = time.time() - start_time
            self.performance_tracker.track('generate_questions', duration)
            
            if summary_parts:
                shuffle_status = "已打乱" if shuffle_enabled else "未打乱"
                logger.info(f"题目生成完成 ({shuffle_status}): {', '.join(summary_parts)}, 总计 {len(result_indices)} 道, 耗时 {duration:.3f}s")
            
            return result_indices
            
        except Exception as e:
            logger.error(f"题目生成失败: {e}")
            return []


class PracticeService:
    """高性能练习服务"""
    
    def __init__(self, cache_manager: Optional[HybridCacheManager] = None):
        self.cache_manager = cache_manager or HybridCacheManager()
        self.question_generator = QuestionGenerator()
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="practice_")
    
    def get_question_bank_optimized(self, tiku_id: int) -> List[Dict[str, Any]]:
        """获取优化的题库数据"""
        start_time = time.time()
        
        # 尝试从缓存获取
        cached_questions = self.cache_manager.get_question_bank(tiku_id)
        if cached_questions:
            logger.debug(f"使用缓存的题目数据，题库ID: {tiku_id}, 耗时: {time.time() - start_time:.3f}s")
            return cached_questions
        
        logger.info(f"从数据库获取题库 {tiku_id} 的题目数据")
        try:
            # 从数据库获取题目列表
            question_bank_list = get_questions_by_tiku(tiku_id)
            
            if not question_bank_list:
                logger.warning(f"题库 {tiku_id} 为空或不存在")
                return []
            
            # 存储到缓存
            self.cache_manager.set_question_bank(tiku_id, question_bank_list)
            
            duration = time.time() - start_time
            logger.info(f"成功缓存题库 {tiku_id} 的 {len(question_bank_list)} 道题目，耗时: {duration:.3f}s")
            return question_bank_list
            
        except Exception as e:
            logger.error(f"获取题库 {tiku_id} 的题目数据失败: {e}")
            return []
    
    def generate_practice_questions(self, tiku_id: int, selected_types: Optional[List[str]] = None,
                                  shuffle_enabled: bool = True) -> Tuple[List[int], List[Dict[str, Any]]]:
        """生成练习题目索引和题库数据"""
        # 获取题库数据
        question_bank = self.get_question_bank_optimized(tiku_id)
        if not question_bank:
            return [], []
        
        # 生成题目索引
        question_indices = self.question_generator.generate_question_indices(
            question_bank, selected_types, shuffle_enabled
        )
        
        return question_indices, question_bank
    
    def get_current_question(self, question_bank: List[Dict[str, Any]], 
                           question_indices: List[int], current_index: int) -> Optional[Dict[str, Any]]:
        """获取当前题目数据"""
        if not question_indices or current_index >= len(question_indices):
            return None
        
        question_index = question_indices[current_index]
        if question_index >= len(question_bank):
            return None
        
        question_obj = question_bank[question_index]
        
        # 格式化题目数据
        return {
            'id': question_obj['id'],
            'type': question_obj['type'],
            'question': question_obj['question'],
            'options_for_practice': question_obj.get('options_for_practice'),
            'answer': question_obj['answer'],
            'is_multiple_choice': question_obj.get('is_multiple_choice', False),
            'analysis': question_obj.get('explanation', '暂无解析'),
            'knowledge_points': question_obj.get('knowledge_points', [])
        }
    
    def validate_and_process_answer(self, question_data: Dict[str, Any], 
                                  user_answer: str, peeked: bool = False) -> Dict[str, Any]:
        """验证并处理答案"""
        is_multiple_choice = question_data.get('is_multiple_choice', False)
        correct_answer = question_data['answer'].upper()
        user_answer_upper = user_answer.upper()
        
        # 判断答案正确性
        is_correct = False if peeked else validate_answer(user_answer_upper, correct_answer, is_multiple_choice)
        
        # 格式化答案显示
        options = question_data.get('options_for_practice', {})
        user_answer_display = '未作答（直接查看答案）' if peeked else format_answer_display(
            user_answer_upper, options, is_multiple_choice)
        correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)
        
        return {
            'is_correct': is_correct,
            'user_answer_display': user_answer_display,
            'correct_answer_display': correct_answer_display,
            'user_answer': user_answer_upper,
            'correct_answer': correct_answer
        }
    
    def get_question_by_id_optimized(self, question_id: str) -> Optional[Dict[str, Any]]:
        """优化的根据ID获取题目"""
        if not question_id.startswith('db_'):
            return None
        
        try:
            db_id = int(question_id.replace('db_', ''))
        except ValueError:
            return None
        
        # 使用优化的数据库查询
        question_data = get_question_by_db_id(db_id)
        if not question_data:
            return None
        
        # 添加答案显示格式
        options = question_data.get('options_for_practice', {})
        is_multiple_choice = question_data.get('is_multiple_choice', False)
        correct_answer = question_data.get('answer', '').upper()
        correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)
        
        question_data['correct_answer_display'] = correct_answer_display
        return question_data
    
    def calculate_round_transition(self, current_indices: List[int], wrong_indices: List[int],
                                 shuffle_enabled: bool = True) -> Tuple[bool, List[int], int]:
        """计算轮次转换"""
        if not wrong_indices:
            # 没有错题，练习完成
            return True, [], 0
        
        # 开始新轮次
        new_round_indices = list(wrong_indices)
        if shuffle_enabled:
            random.shuffle(new_round_indices)
        
        return False, new_round_indices, len(new_round_indices)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'question_generator': self.question_generator.performance_tracker.get_stats(),
            'service_info': {
                'cache_enabled': self.cache_manager is not None,
                'executor_active': hasattr(self, '_executor')
            }
        }
    
    def batch_process_questions(self, question_bank: List[Dict[str, Any]], 
                              indices: List[int]) -> List[Dict[str, Any]]:
        """批量处理题目数据"""
        result = []
        for idx in indices:
            if idx < len(question_bank):
                question = question_bank[idx]
                formatted_question = self.get_current_question(question_bank, [idx], 0)
                if formatted_question:
                    result.append(formatted_question)
        return result
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False) 