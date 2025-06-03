"""
会话管理模块 - 包含session相关的所有操作
"""
import logging
from typing import Any, Optional, List
from flask import session
from .config import SESSION_KEYS
from .connectDB import save_user_session, load_user_session

logger = logging.getLogger(__name__)


def get_session_value(key: str, default: Any = None) -> Any:
    """安全获取session值"""
    return session.get(key, default)


def set_session_value(key: str, value: Any) -> None:
    """安全设置session值"""
    session[key] = value
    session.modified = True


def get_user_session_info() -> dict:
    """获取当前用户的session信息"""
    return {
        'user_id': get_session_value(SESSION_KEYS['USER_ID']),
        'username': get_session_value(SESSION_KEYS['USERNAME']),
        'is_authenticated': bool(get_session_value(SESSION_KEYS['USER_ID']))
    }


def clear_practice_session() -> None:
    """清除练习相关的session数据"""
    # 定义需要清除的练习相关键
    practice_keys = [
        SESSION_KEYS['CURRENT_TIKU_ID'],
        SESSION_KEYS['QUESTION_INDICES'],
        SESSION_KEYS['CURRENT_INDEX'],
        SESSION_KEYS['WRONG_INDICES'],
        SESSION_KEYS['ROUND_NUMBER'],
        SESSION_KEYS['INITIAL_TOTAL'],
        SESSION_KEYS['CORRECT_FIRST_TRY'],
        SESSION_KEYS['QUESTION_STATUSES'],
        SESSION_KEYS['ANSWER_HISTORY']
    ]

    for key in practice_keys:
        session.pop(key, None)
    session.modified = True


def clear_all_session() -> None:
    """清除所有session数据"""
    session.clear()


def get_practice_session_summary() -> dict:
    """获取练习session的摘要信息"""
    return {
        'current_tiku_id': get_session_value(SESSION_KEYS['CURRENT_TIKU_ID']),
        'total_questions': len(get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])),
        'current_index': get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0),
        'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1),
        'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
        'has_active_practice': bool(get_session_value(SESSION_KEYS['CURRENT_TIKU_ID']))
    }


def save_session_to_db() -> None:
    """保存当前session到数据库"""
    user_id = session.get('user_id')
    if user_id:
        session_data = {key: session.get(key) for key in SESSION_KEYS.values() if key in session}
        if session_data:
            save_user_session(user_id, session_data)


def load_session_from_db() -> None:
    """从数据库加载session数据"""
    user_id = session.get('user_id')
    if user_id:
        user_session_data = load_user_session(user_id)
        if user_session_data:
            for key, value in user_session_data.items():
                session[key] = value
            session.modified = True


def get_tiku_position_by_id(tiku_id: int) -> Optional[str]:
    """根据题库ID获取题库位置标识符"""
    if not tiku_id:
        return None
    
    try:
        from .connectDB import get_tiku_by_subject
        tiku_list = get_tiku_by_subject()
        
        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                return tiku['tiku_position']
        
        return None
    except Exception as e:
        logger.error(f"获取题库位置失败: {e}")
        return None


def get_current_tiku_info() -> Optional[dict]:
    """获取当前练习题库的详细信息"""
    tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not tiku_id:
        return None
    
    try:
        from .connectDB import get_tiku_by_subject
        tiku_list = get_tiku_by_subject()
        
        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                return tiku
        
        return None
    except Exception as e:
        logger.error(f"获取题库信息失败: {e}")
        return None 