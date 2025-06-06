"""
会话管理模块 - 包含session相关的所有操作
适配Flask-Session，所有session数据统一存储在Redis中
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Optional, Dict

import redis
from flask import session, g

from backend.config import RedisConfig
from .RedisManager import redis_manager
from .config import SESSION_KEYS, Config
from .connectDB import (
    create_practice_session, update_practice_session,
    complete_practice_session, get_user_active_practice_session,
    get_tiku_by_subject
)

logger = logging.getLogger(__name__)

# 添加练习会话ID的session key
PRACTICE_SESSION_ID_KEY = 'practice_session_id'


class SessionManager:
    """简化的Session管理器，完全依赖Flask-Session"""

    def __init__(self):
        self._redis_manager = redis_manager

    @staticmethod
    def create_session_redis():
        # 配置 Redis 连接用于 Flask-Session
        try:
            redis_client = redis.Redis(
                host=RedisConfig.REDIS_HOST,
                port=RedisConfig.REDIS_PORT,
                db=RedisConfig.SESSION_DB,
                password=RedisConfig.REDIS_PASSWORD,
                decode_responses=False,  # 修改为False，避免UTF-8解码问题
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )

            # 测试Redis连接
            redis_client.ping()
            redis_client.flushdb()

            logger.info("Flask-Session Redis连接成功")
            return redis_client

        except Exception as e:
            logger.error(f"Redis连接失败，Flask-Session将回退到文件系统: {e}")
            # 如果Redis不可用，直接退出
            exit(-1)

    @property
    def redis_available(self) -> bool:
        """检查Redis是否可用"""
        return self._redis_manager.is_available

    @staticmethod
    def get_session_info() -> Dict[str, Any]:
        """获取session状态信息 - 简化版本，依赖Flask-Session"""
        return {
            'is_authenticated': bool(session.get(SESSION_KEYS['USER_ID'])),
            'user_id': session.get(SESSION_KEYS['USER_ID']),
            'username': session.get(SESSION_KEYS['USERNAME']),
            'session_valid': True,  # Flask-Session会自动处理过期
            'storage_info': SessionManager._get_storage_info()
        }

    @staticmethod
    def _get_storage_info() -> Dict[str, str]:
        """获取存储信息 - 适配Flask-Session"""
        try:
            from flask import current_app
            session_type = current_app.config.get('SESSION_TYPE', 'unknown')
        except RuntimeError:
            # 在没有应用上下文时
            session_type = 'unknown'

        # Flask-Session 0.8.0可能使用不同的session ID键
        session_id = session.get('sid', session.get('_id', session.get('session_id', 'N/A')))

        return {
            'session_type': session_type,
            'session_id': session_id,
            'storage_strategy': f'Flask-Session ({session_type})',
            'redis_available': redis_manager.is_available if session_type == 'redis' else 'N/A'
        }


# 创建全局session管理器实例
session_manager = SessionManager()


def get_session_value(key: str, default: Any = None) -> Any:
    """
    获取session值 - 适配Flask-Session
    Flask-Session统一管理所有session数据，无需区分大小数据
    """
    result = session.get(key, default)
    logger.debug(f"获取session key {key}: {'有值' if result is not None else '无值/默认值'}")
    return result


def set_session_value(key: str, value: Any) -> None:
    """
    设置session值 - 适配Flask-Session
    Flask-Session统一管理所有session数据，无需区分大小数据
    """
    logger.debug(f"设置session key {key}: 长度 {len(value) if hasattr(value, '__len__') else 'N/A'}")
    session[key] = value
    # Flask-Session会自动处理session.modified


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
    """获取用户会话信息 - 简化版本，完全依赖Flask-Session"""
    user_id = session.get(SESSION_KEYS['USER_ID'])
    username = session.get(SESSION_KEYS['USERNAME'])
    user_model = session.get(SESSION_KEYS['USER_MODEL'], 0)

    if user_id and username:
        return {
            'user_id': user_id,
            'username': username,
            'user_model': user_model,
            'email': '',  # 如果需要email，可以从数据库查询
            'session_id': session.get('sid', session.get('_id', ''))
        }

    # 如果没有登录，返回空信息
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
    user_id = session.get(SESSION_KEYS['USER_ID'])
    if user_id:
        logger.debug("尝试从练习会话数据库恢复会话")
        try:
            check_and_resume_practice_session(user_id)
        except Exception as e:
            logger.warning(f"从数据库恢复session失败: {e}")


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
                return tiku  # Return the whole tiku dict

        logger.warning(f"在数据库中未找到当前 tiku_id: {tiku_id}")
        return None
    except Exception as e:
        logger.error(f"获取当前题库信息失败: {e}")
        return None
