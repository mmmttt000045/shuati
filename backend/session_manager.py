"""
会话管理模块 - 包含session相关的所有操作
支持Redis + 数据库的混合存储方式
"""
import logging
import time

from datetime import datetime, timedelta
from typing import Any, Optional, List, Dict
from flask import session, request, g

from .config import SESSION_KEYS, Config
from .RedisManager import get_hybrid_session_value, set_hybrid_session_value, redis_manager
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

# 优化：大数据存储在Redis/数据库中的keys - 这些不应该存储在cookie中
LARGE_DATA_KEYS = {
    SESSION_KEYS['QUESTION_INDICES'],
    SESSION_KEYS['WRONG_INDICES'], 
    SESSION_KEYS['QUESTION_STATUSES'],
    SESSION_KEYS['ANSWER_HISTORY']
}


class SessionManager:
    """增强的Session管理器，支持Redis混合存储"""
    
    def __init__(self):
        self._redis_manager = redis_manager
    
    @property
    def redis_available(self) -> bool:
        """检查Redis是否可用"""
        return self._redis_manager.is_available
    
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
        
        # 同时更新Redis session的TTL
        session_id = session.get('session_id')
        if session_id:
            redis_manager.extend_session_ttl(session_id)
    
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
            'warning_needed': False,
            'storage_info': SessionManager._get_storage_info()
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
    def _get_storage_info() -> Dict[str, str]:
        """获取存储信息"""
        return {
            'redis_available': redis_manager.is_available,
            'session_id': session.get('session_id'),
            'storage_strategy': 'Redis+DB' if redis_manager.is_available else 'Database'
        }
    
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
            
            # 清理Redis数据
            session_id = session.get('session_id')
            if session_id:
                redis_manager.delete_session_data(session_id)
            
            session.clear()
            return True
        return False


# 创建全局session管理器实例
session_manager = SessionManager()


def get_session_value(key: str, default: Any = None) -> Any:
    """
    混合session值获取 - 大数据优先从Redis获取，回退到数据库，小数据从cookie获取
    """
    # 如果是大数据key，使用混合存储策略
    if key in LARGE_DATA_KEYS:
        try:
            result = get_hybrid_session_value(key, default)
            logger.debug(f"获取大数据key {key}: {'有值' if result is not None else '无值/默认值'} (长度: {len(result) if hasattr(result, '__len__') else 'N/A'})")
            return result
        except Exception as e:
            logger.error(f"获取大数据key {key} 失败: {e}")
            return default
    
    # 小数据从cookie获取
    result = session.get(key, default)
    logger.debug(f"获取小数据key {key}: {'有值' if result is not None else '无值/默认值'}")
    return result


def set_session_value(key: str, value: Any) -> None:
    """
    混合session值设置 - 大数据存储在Redis/数据库，小数据存储在cookie
    """
    # 如果是大数据key，使用混合存储策略
    if key in LARGE_DATA_KEYS:
        try:
            logger.debug(f"设置大数据key {key}: 长度 {len(value) if hasattr(value, '__len__') else 'N/A'}")
            set_hybrid_session_value(key, value)
            # 验证存储
            verification = get_hybrid_session_value(key, None)
            if verification is not None:
                logger.info(f"✓ 大数据key {key} 存储验证成功")
            else:
                logger.warning(f"✗ 大数据key {key} 存储验证失败")
            return
        except Exception as e:
            logger.error(f"设置大数据key {key} 失败: {e}")
            return
    
    # 小数据存储在cookie
    logger.debug(f"设置小数据key {key} 到cookie")
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
    """获取用户会话信息 - 兼容新的SessionAuth系统"""
    # 优先从Flask的g对象获取当前用户信息（由@login_required设置）
    current_user = getattr(g, 'current_user', None)
    
    if current_user:
        return {
            'user_id': current_user['user_id'],
            'username': current_user['username'],
            'user_model': current_user.get('user_model', 0),
            'email': current_user.get('email', ''),
            'session_id': current_user.get('session_id', '')
        }
    
    # 回退到Flask session（兼容性处理）
    user_id = session.get(SESSION_KEYS['USER_ID'])
    username = session.get(SESSION_KEYS['USERNAME'])
    
    if user_id and username:
        return {
            'user_id': user_id,
            'username': username,
            'user_model': 0,  # 默认值
            'email': '',
            'session_id': session.get('session_id', '')
        }
    
    # 如果都没有，返回空信息
    return {
        'user_id': None,
        'username': None,
        'user_model': 0,
        'email': '',
        'session_id': ''
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
    logger.debug(f"开始检查用户 {user_id} 的活跃练习会话")

    try:
        active_session = get_user_active_practice_session(user_id, tiku_id)
        logger.debug(f"查询活跃会话结果: {active_session is not None}")

        if active_session:
            logger.debug(f"找到活跃会话: session_id={active_session['id']}, tiku_id={active_session.get('tiku_id')}")

            # 只将会话ID和基本信息存储到Flask session中，大数据保留在数据库
            session_data_to_set = {
                PRACTICE_SESSION_ID_KEY: active_session['id'],
                SESSION_KEYS['CURRENT_TIKU_ID']: active_session['tiku_id'],
                SESSION_KEYS['CURRENT_INDEX']: active_session.get('current_question_index', 0),
                SESSION_KEYS['ROUND_NUMBER']: active_session.get('round_number', 1),
                SESSION_KEYS['INITIAL_TOTAL']: active_session.get('total_questions', 0),
                SESSION_KEYS['CORRECT_FIRST_TRY']: active_session.get('correct_first_try', 0),
                SESSION_KEYS['SELECT_TYPES']: active_session.get('selected_types', []),
            }

            logger.debug(f"准备设置的 session 数据: {session_data_to_set}")

            for key, value in session_data_to_set.items():
                session[key] = value

            session.modified = True

            # 验证设置是否成功
            verification_tiku_id = session.get(SESSION_KEYS['CURRENT_TIKU_ID'])
            logger.debug(f"验证设置结果: 期望 tiku_id={active_session['tiku_id']}, 实际={verification_tiku_id}")

            if verification_tiku_id != active_session['tiku_id']:
                logger.error(f"Session 设置验证失败！期望: {active_session['tiku_id']}, 实际: {verification_tiku_id}")
                return None

            # 大数据（question_indices, wrong_indices, question_statuses, answer_history）
            from backend.routes.practice import set_session_value
            set_session_value(SESSION_KEYS['QUESTION_INDICES'], active_session['question_indices'])
            set_session_value(SESSION_KEYS['WRONG_INDICES'], active_session['wrong_indices'])
            set_session_value(SESSION_KEYS['QUESTION_STATUSES'], active_session['question_statuses'])
            set_session_value(SESSION_KEYS['ANSWER_HISTORY'], active_session['answer_history'])

            logger.info(f"恢复活跃练习会话成功: session_id={active_session['id']}, tiku_id={active_session['tiku_id']}")
            return active_session
        else:
            logger.debug(f"用户 {user_id} 没有活跃的练习会话")

        return None

    except Exception as e:
        logger.error(f"检查活跃练习会话异常: {e}")
        import traceback
        logger.error(f"检查活跃练习会话异常详情: {traceback.format_exc()}")
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