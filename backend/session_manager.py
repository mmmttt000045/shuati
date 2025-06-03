"""
会话管理模块 - 包含session相关的所有操作
"""
import logging
from typing import Any, Optional
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


def clear_practice_session() -> None:
    """清除练习相关的session数据"""
    practice_keys = [
        SESSION_KEYS['CURRENT_EXCEL_FILE'], SESSION_KEYS['QUESTION_INDICES'],
        SESSION_KEYS['CURRENT_INDEX'], SESSION_KEYS['WRONG_INDICES'],
        SESSION_KEYS['ROUND_NUMBER'], SESSION_KEYS['INITIAL_TOTAL'],
        SESSION_KEYS['CORRECT_FIRST_TRY'], SESSION_KEYS['QUESTION_STATUSES'],
        SESSION_KEYS['ANSWER_HISTORY']
    ]

    for key in practice_keys:
        session.pop(key, None)
    session.modified = True


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