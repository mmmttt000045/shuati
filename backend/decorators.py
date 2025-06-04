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


class UserPermissionCache:
    """用户权限缓存管理类"""
    
    def __init__(self, cache_ttl: int = 300):  # 缓存5分钟
        self._cache: Dict[int, Dict] = {}
        self._cache_ttl = cache_ttl
    
    def get_user_model(self, user_id: int) -> Optional[int]:
        """获取用户权限模型，优先从缓存获取"""
        current_time = time.time()
        
        # 检查缓存是否存在且未过期
        if user_id in self._cache:
            cache_entry = self._cache[user_id]
            if current_time - cache_entry['timestamp'] < self._cache_ttl:
                logger.debug(f"从缓存获取用户权限: user_id={user_id}, model={cache_entry['model']}")
                return cache_entry['model']
            else:
                # 缓存过期，删除
                del self._cache[user_id]
        
        # 从数据库获取
        user_model = get_user_model(user_id)
        
        # 存入缓存
        if user_model is not None:
            self._cache[user_id] = {
                'model': user_model,
                'timestamp': current_time
            }
            logger.debug(f"缓存用户权限: user_id={user_id}, model={user_model}")
        
        return user_model
    
    def update_user_model(self, user_id: int, model: int) -> bool:
        """更新缓存中的用户权限模型"""
        try:
            current_time = time.time()
            self._cache[user_id] = {
                'model': model,
                'timestamp': current_time
            }
            logger.info(f"更新用户权限缓存: user_id={user_id}, model={model}")
            return True
        except Exception as e:
            logger.error(f"更新用户权限缓存失败: {e}")
            return False

# 创建全局缓存实例
permission_cache = UserPermissionCache()


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
    """检查用户是否已登录的装饰器 - 优化版本，支持session过期检测"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 导入session管理器（避免循环导入）
        from .session_manager import session_manager
        
        user_id = session.get('user_id')
        username = session.get('username')

        if not user_id or not username:
            return create_response(False, '请先登录', status_code=401)
        
        # 检查session是否过期
        if session_manager.is_session_expired():
            logger.info(f"Session过期，清理用户session: user_id={user_id}")
            session_manager.cleanup_expired_session()
            return create_response(False, 'Session已过期，请重新登录', status_code=401)
        
        # 更新session活跃度
        session_manager.update_activity()

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """检查用户是否为管理员的装饰器（使用缓存）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return create_response(False, '请先登录', status_code=401)

        # 使用缓存获取用户权限
        user_model = permission_cache.get_user_model(user_id)
        if user_model != 10:  # ROOT用户
            return create_response(False, '权限不足，需要管理员权限', status_code=403)

        return f(*args, **kwargs)
    return decorated_function 