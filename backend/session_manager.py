"""
会话管理模块 - 包含session相关的所有操作
"""
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from flask import session, request, g
from .config import SESSION_KEYS, Config
from .connectDB import (
    create_practice_session, update_practice_session, 
    complete_practice_session, get_user_active_practice_session,
    get_tiku_by_subject
)

logger = logging.getLogger(__name__)

# 添加练习会话ID的session key
PRACTICE_SESSION_ID_KEY = 'practice_session_id'

# Session活跃度管理相关常量
SESSION_LAST_ACTIVITY_KEY = 'last_activity'
SESSION_LOGIN_TIME_KEY = 'login_time'
SESSION_WARNING_SHOWN_KEY = 'warning_shown'

# 优化：大数据存储在数据库中的keys - 这些不应该存储在cookie中
DATABASE_STORED_KEYS = {
    SESSION_KEYS['QUESTION_INDICES'],
    SESSION_KEYS['WRONG_INDICES'], 
    SESSION_KEYS['QUESTION_STATUSES'],
    SESSION_KEYS['ANSWER_HISTORY']
}


class SessionManager:
    """优化的Session管理器"""
    
    @staticmethod
    def update_activity():
        """更新session活跃度"""
        current_time = datetime.now()
        session[SESSION_LAST_ACTIVITY_KEY] = current_time.isoformat()
        
        # 如果是新session，记录登录时间
        if SESSION_LOGIN_TIME_KEY not in session:
            session[SESSION_LOGIN_TIME_KEY] = current_time.isoformat()
        
        session.modified = True
        session.permanent = True
    
    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """获取session状态信息"""
        now = datetime.now()
        
        # 获取活跃度信息
        last_activity_str = session.get(SESSION_LAST_ACTIVITY_KEY)
        login_time_str = session.get(SESSION_LOGIN_TIME_KEY)
        
        result = {
            'is_authenticated': bool(session.get(SESSION_KEYS['USER_ID'])),
            'user_id': session.get(SESSION_KEYS['USER_ID']),
            'username': session.get(SESSION_KEYS['USERNAME']),
            'last_activity': last_activity_str,
            'login_time': login_time_str,
            'session_valid': True,
            'time_remaining': None,
            'warning_needed': False
        }
        
        if last_activity_str:
            try:
                last_activity = datetime.fromisoformat(last_activity_str)
                session_age = now - last_activity
                
                # 检查session是否过期
                if session_age > Config.PERMANENT_SESSION_LIFETIME:
                    result['session_valid'] = False
                    result['expired'] = True
                else:
                    # 计算剩余时间
                    remaining = Config.PERMANENT_SESSION_LIFETIME - session_age
                    result['time_remaining'] = int(remaining.total_seconds())
                    
                    # 检查是否需要警告
                    warning_threshold = timedelta(minutes=Config.SESSION_WARNING_MINUTES)
                    if remaining <= warning_threshold and not session.get(SESSION_WARNING_SHOWN_KEY):
                        result['warning_needed'] = True
                        
            except (ValueError, TypeError) as e:
                logger.warning(f"解析session时间失败: {e}")
                result['session_valid'] = False
        
        return result
    
    @staticmethod
    def mark_warning_shown():
        """标记已显示过期警告"""
        session[SESSION_WARNING_SHOWN_KEY] = True
        session.modified = True
    
    @staticmethod
    def is_session_expired() -> bool:
        """检查session是否过期"""
        last_activity_str = session.get(SESSION_LAST_ACTIVITY_KEY)
        if not last_activity_str:
            return True
            
        try:
            last_activity = datetime.fromisoformat(last_activity_str)
            session_age = datetime.now() - last_activity
            return session_age > Config.PERMANENT_SESSION_LIFETIME
        except (ValueError, TypeError):
            return True
    
    @staticmethod
    def extend_session():
        """延长session时间（重新活跃）"""
        SessionManager.update_activity()
        # 清除警告标记
        session.pop(SESSION_WARNING_SHOWN_KEY, None)
        session.modified = True
    
    @staticmethod
    def cleanup_expired_session():
        """清理过期的session"""
        if SessionManager.is_session_expired():
            logger.info(f"清理过期session: user_id={session.get(SESSION_KEYS['USER_ID'])}")
            session.clear()
            return True
        return False


# 创建全局session管理器实例
session_manager = SessionManager()


def get_session_value(key: str, default: Any = None) -> Any:
    """
    优化的session值获取 - 大数据从数据库获取，小数据从cookie获取
    """
    # 如果是大数据key，从数据库获取
    if key in DATABASE_STORED_KEYS:
        return get_database_session_value(key, default)
    
    # 小数据从cookie获取
    return session.get(key, default)


def set_session_value(key: str, value: Any) -> None:
    """
    优化的session值设置 - 大数据存储在数据库，小数据存储在cookie
    """
    # 如果是大数据key，存储到数据库
    if key in DATABASE_STORED_KEYS:
        set_database_session_value(key, value)
        return
    
    # 小数据存储在cookie
    session[key] = value
    session.modified = True


def get_database_session_value(key: str, default: Any = None) -> Any:
    """从数据库获取session数据"""
    session_id = session.get(PRACTICE_SESSION_ID_KEY)
    if not session_id:
        return default
    
    try:
        from .connectDB import get_practice_session
        session_data = get_practice_session(session_id)
        
        if not session_data:
            return default
        
        # 映射session key到数据库字段
        key_mapping = {
            SESSION_KEYS['QUESTION_INDICES']: 'question_indices',
            SESSION_KEYS['WRONG_INDICES']: 'wrong_indices',
            SESSION_KEYS['QUESTION_STATUSES']: 'question_statuses',
            SESSION_KEYS['ANSWER_HISTORY']: 'answer_history'
        }
        
        db_field = key_mapping.get(key)
        if db_field and db_field in session_data:
            return session_data[db_field]
            
        return default
        
    except Exception as e:
        logger.error(f"从数据库获取session数据失败: {e}")
        return default


def set_database_session_value(key: str, value: Any) -> None:
    """设置数据库session数据"""
    session_id = session.get(PRACTICE_SESSION_ID_KEY)
    if not session_id:
        logger.warning(f"尝试设置数据库session值 {key}，但没有找到session ID")
        return
    
    try:
        # 映射session key到数据库字段
        key_mapping = {
            SESSION_KEYS['QUESTION_INDICES']: 'question_indices',
            SESSION_KEYS['WRONG_INDICES']: 'wrong_indices',
            SESSION_KEYS['QUESTION_STATUSES']: 'question_statuses',
            SESSION_KEYS['ANSWER_HISTORY']: 'answer_history'
        }
        
        db_field = key_mapping.get(key)
        if db_field:
            update_data = {db_field: value}
            update_current_practice_session(**update_data)
        
    except Exception as e:
        logger.error(f"设置数据库session数据失败: {e}")


def get_user_session_info() -> dict:
    """获取当前用户的session信息"""
    return {
        'user_id': get_session_value(SESSION_KEYS['USER_ID']),
        'username': get_session_value(SESSION_KEYS['USERNAME']),
        'is_authenticated': bool(get_session_value(SESSION_KEYS['USER_ID']))
    }


def create_and_store_practice_session(user_id: int, tiku_id: int, session_type: str = 'normal',
                                    shuffle_enabled: bool = True, selected_types: list = None,
                                    total_questions: int = 0, question_indices: list = None) -> Optional[int]:
    """创建练习会话并存储到数据库和Flask session中 - 优化版本"""
    try:
        result = create_practice_session(
            user_id=user_id,
            tiku_id=tiku_id,
            session_type=session_type,
            shuffle_enabled=shuffle_enabled,
            selected_types=selected_types,
            total_questions=total_questions,
            question_indices=question_indices
        )
        
        if result['success']:
            session_id = result['session_id']
            # 只将会话ID和基本信息存储到Flask session cookie中
            session[PRACTICE_SESSION_ID_KEY] = session_id
            session[SESSION_KEYS['CURRENT_TIKU_ID']] = tiku_id
            session[SESSION_KEYS['CURRENT_INDEX']] = 0
            session[SESSION_KEYS['ROUND_NUMBER']] = 1
            session[SESSION_KEYS['INITIAL_TOTAL']] = total_questions
            session[SESSION_KEYS['CORRECT_FIRST_TRY']] = 0
            session.modified = True
            
            logger.info(f"创建练习会话成功: session_id={session_id} (大数据存储在数据库中)")
            return session_id
        else:
            logger.error(f"创建练习会话失败: {result['error']}")
            return None
            
    except Exception as e:
        logger.error(f"创建练习会话异常: {e}")
        return None


def update_current_practice_session(**kwargs) -> bool:
    """更新当前的练习会话"""
    session_id = session.get(PRACTICE_SESSION_ID_KEY)
    if not session_id:
        logger.warning("没有找到当前练习会话ID")
        return False
        
    try:
        result = update_practice_session(session_id, **kwargs)
        if result['success']:
            logger.debug(f"更新练习会话成功: session_id={session_id}")
            return True
        else:
            logger.error(f"更新练习会话失败: {result['error']}")
            return False
            
    except Exception as e:
        logger.error(f"更新练习会话异常: {e}")
        return False


def complete_current_practice_session(final_stats: dict = None) -> bool:
    """完成当前的练习会话 - 优化版本"""
    session_id = session.get(PRACTICE_SESSION_ID_KEY)
    if not session_id:
        logger.warning("没有找到当前练习会话ID")
        return False
        
    try:
        result = complete_practice_session(session_id, final_stats)
        if result['success']:
            # 清除Flask session中的会话ID和所有练习相关数据
            session.pop(PRACTICE_SESSION_ID_KEY, None)
            session.pop(SESSION_KEYS['CURRENT_TIKU_ID'], None)
            session.pop(SESSION_KEYS['CURRENT_INDEX'], None)
            session.pop(SESSION_KEYS['ROUND_NUMBER'], None)
            session.pop(SESSION_KEYS['INITIAL_TOTAL'], None)
            session.pop(SESSION_KEYS['CORRECT_FIRST_TRY'], None)
            session.modified = True
            
            logger.info(f"完成练习会话成功: session_id={session_id}")
            return True
        else:
            logger.error(f"完成练习会话失败: {result['error']}")
            return False
            
    except Exception as e:
        logger.error(f"完成练习会话异常: {e}")
        return False


def get_current_practice_session_id() -> Optional[int]:
    """获取当前练习会话ID"""
    return session.get(PRACTICE_SESSION_ID_KEY)


def check_and_resume_practice_session(user_id: int, tiku_id: int = None) -> Optional[dict]:
    """检查并恢复用户的活跃练习会话 - 优化版本：只存储关键信息到cookie"""
    try:
        active_session = get_user_active_practice_session(user_id, tiku_id)
        if active_session:
            # 只将会话ID和基本信息存储到Flask session中，大数据保留在数据库
            session[PRACTICE_SESSION_ID_KEY] = active_session['id']
            session[SESSION_KEYS['CURRENT_TIKU_ID']] = active_session['tiku_id']
            session[SESSION_KEYS['CURRENT_INDEX']] = active_session.get('current_question_index', 0)
            session[SESSION_KEYS['ROUND_NUMBER']] = active_session.get('round_number', 1)
            session[SESSION_KEYS['INITIAL_TOTAL']] = active_session.get('total_questions', 0)
            session[SESSION_KEYS['CORRECT_FIRST_TRY']] = active_session.get('correct_first_try', 0)
            session.modified = True
            
            # 大数据（question_indices, wrong_indices, question_statuses, answer_history）
            # 已经在数据库中，通过get_session_value会自动从数据库获取
            
            logger.info(f"恢复活跃练习会话: session_id={active_session['id']}")
            return active_session
        
        return None
        
    except Exception as e:
        logger.error(f"检查活跃练习会话异常: {e}")
        return None


def clear_practice_session() -> None:
    """清除练习相关的session数据 - 优化版本：只清除cookie中的数据"""
    # 只清除cookie中的练习相关键（大数据在数据库中会通过会话管理自动清理）
    practice_keys = [
        SESSION_KEYS['CURRENT_TIKU_ID'],
        SESSION_KEYS['CURRENT_INDEX'],
        SESSION_KEYS['WRONG_INDICES'],
        SESSION_KEYS['ROUND_NUMBER'],
        SESSION_KEYS['INITIAL_TOTAL'],
        SESSION_KEYS['CORRECT_FIRST_TRY'],
        PRACTICE_SESSION_ID_KEY  # 清除会话ID以断开与数据库的连接
    ]

    for key in practice_keys:
        session.pop(key, None)
    session.modified = True
    
    # 大数据在数据库中，会话结束时会自动标记为完成状态


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
        'has_active_practice': bool(get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])),
        'practice_session_id': get_current_practice_session_id()  # 新增：包含练习会话ID
    }


def load_session_from_db() -> None:
    """
    从数据库加载session数据 - 现在通过练习会话系统处理
    使用 check_and_resume_practice_session 来恢复活跃的练习会话
    """
    user_id = session.get('user_id')
    if user_id:
        logger.debug("尝试从练习会话数据库恢复会话")
        check_and_resume_practice_session(user_id)


def get_tiku_position_by_id(tiku_id: int) -> Optional[str]:
    """根据题库ID获取题库位置标识符 (直接从数据库查询)"""
    if not tiku_id:
        return None
    
    try:
        # 直接从数据库获取题库列表，避免循环依赖
        tiku_list = get_tiku_by_subject()
        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                return tiku['tiku_position']
        
        logger.warning(f"在数据库中未找到 tiku_id: {tiku_id}")
        return None
    except Exception as e:
        logger.error(f"获取题库位置失败: {e}")
        return None


def get_current_tiku_info() -> Optional[dict]:
    """获取当前练习题库的详细信息 (直接从数据库查询)"""
    tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not tiku_id:
        return None
    
    try:
        # Ensure tiku_id is an integer if it comes from session and might be stringified
        tiku_id = int(tiku_id)
    except ValueError:
        logger.error(f"当前题库ID格式无效: {tiku_id}")
        return None

    try:
        # 直接从数据库获取题库列表，避免循环依赖
        tiku_list = get_tiku_by_subject()
        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                return tiku # Return the whole tiku dict
        
        logger.warning(f"在数据库中未找到当前 tiku_id: {tiku_id}")
        return None
    except Exception as e:
        logger.error(f"获取当前题库信息失败: {e}")
        return None 