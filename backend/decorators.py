"""
装饰器模块 - 包含所有的装饰器函数
"""
import logging
import time
from functools import wraps
from typing import Dict, Optional
from flask import session
from werkzeug.exceptions import NotFound, BadRequest
from .utils import create_response
from .connectDB import get_user_model

logger = logging.getLogger(__name__)

def handle_api_error(func):
    """统一的API错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BadRequest as e:
            return create_response(False, str(e), status_code=400)
        except NotFound as e:
            return create_response(False, str(e), status_code=404)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return create_response(False, 'Internal server error', status_code=500)
    return wrapper


def login_required(f):
    """检查用户是否已登录的装饰器 - 完全依赖 Flask-Session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .config import SESSION_KEYS
        
        user_id = session.get(SESSION_KEYS['USER_ID'])
        
        # 只需要检查 user_id，Flask-Session 会自动处理过期等逻辑
        if not user_id:
            return create_response(False, '请先登录', status_code=401)

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """检查用户是否为管理员的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from .config import SESSION_KEYS
        
        user_id = session.get(SESSION_KEYS['USER_ID'])
        if not user_id:
            return create_response(False, '请先登录', status_code=401)

        user_model = session.get(SESSION_KEYS['USER_MODEL'])
        if user_model != 10:  # ROOT用户
            return create_response(False, '权限不足，需要管理员权限', status_code=403)

        return f(*args, **kwargs)
    return decorated_function 