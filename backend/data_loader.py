"""
数据加载器模块 - 专门处理数据库题目数据的加载
"""
import logging
from typing import Dict, Any

from .connectDB import get_all_questions_by_tiku_dict

logger = logging.getLogger(__name__)


def load_all_banks_from_database():
    """从数据库加载所有题目数据（主要加载方法）"""
    logger.info("从数据库加载所有题目数据...")

    try:
        # 直接从数据库获取所有题目，按题库分组
        questions_dict = get_all_questions_by_tiku_dict()
        
        if not questions_dict:
            logger.warning("数据库中没有题目数据")
            return {}

        # 统计信息
        total_questions = sum(len(questions) for questions in questions_dict.values())
        logger.info(f"从数据库成功加载 {len(questions_dict)} 个题库，共 {total_questions} 道题目")
        
        return questions_dict

    except Exception as e:
        logger.error(f"从数据库加载题目失败: {e}")
        return {} 