"""
用户认证相关的路由模块
"""
import logging
from flask import Blueprint, request, session
from werkzeug.exceptions import BadRequest, NotFound

from ..decorators import handle_api_error, login_required
from ..utils import create_response
from ..session_manager import load_session_from_db, save_session_to_db
from ..connectDB import (
    authenticate_user, create_user, verify_invitation_code,
    get_user_info, update_session_timestamp
)

logger = logging.getLogger(__name__)

# 创建蓝图
auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
@handle_api_error
def api_register():
    """用户注册"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    invitation_code = data.get('invitation_code', '').strip()

    # 验证输入
    if not all([username, password, invitation_code]):
        raise BadRequest('用户名、密码和邀请码都不能为空')
    if not (3 <= len(username) <= 20):
        raise BadRequest('用户名长度必须在3-20个字符之间')
    if len(password) < 6:
        raise BadRequest('密码长度至少6个字符')

    # 验证邀请码
    invitation_code_id = verify_invitation_code(invitation_code)
    if not invitation_code_id:
        raise BadRequest('邀请码无效或已过期')

    # 创建用户
    result = create_user(username, password, invitation_code_id)
    if result['success']:
        logger.info(f"User registered: {username}")
        return create_response(True, '注册成功！请登录。')
    else:
        raise BadRequest(result['error'])


@auth_bp.route('/login', methods=['POST'])
@handle_api_error
def api_login():
    """用户登录"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        raise BadRequest('用户名和密码不能为空')

    result = authenticate_user(username, password)
    if result['success']:
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        load_session_from_db()
        update_session_timestamp(result['user_id'])

        # 获取完整的用户信息，包括身份模型
        user_info = get_user_info(result['user_id'])

        logger.info(f"User logged in: {username}")
        return create_response(True, '登录成功', {
            'user': {
                'user_id': user_info['user_id'] if user_info else result['user_id'],
                'username': user_info['username'] if user_info else result['username'],
                'model': user_info.get('model', 0) if user_info else 0
            }
        })
    else:
        raise BadRequest(result['error'])


@auth_bp.route('/logout', methods=['POST'])
@handle_api_error
def api_logout():
    """用户登出"""
    if session.get('user_id'):
        username = session.get('username', 'Unknown')
        save_session_to_db()
        session.clear()
        logger.info(f"User logged out: {username}")
        return create_response(True, '登出成功')
    else:
        raise BadRequest('用户未登录')


@auth_bp.route('/user', methods=['GET'])
@login_required
@handle_api_error
def api_get_user_info():
    """获取当前用户信息"""
    user_id = session.get('user_id')
    user_info = get_user_info(user_id)

    if user_info:
        return create_response(True, data={
            'user': {
                'user_id': user_info['user_id'],
                'username': user_info['username'],
                'is_enabled': user_info['is_enabled'],
                'created_at': user_info['created_at'].isoformat() if user_info['created_at'] else None,
                'model': user_info.get('model', 0)
            }
        })
    else:
        session.clear()
        raise NotFound('用户信息不存在')


@auth_bp.route('/check', methods=['GET'])
@handle_api_error
def api_check_auth():
    """检查登录状态"""
    if session.get('user_id'):
        # 获取完整的用户信息，包括身份模型
        user_id = session.get('user_id')
        user_info = get_user_info(user_id)

        return create_response(True, data={
            'authenticated': True,
            'user': {
                'user_id': user_info['user_id'] if user_info else user_id,
                'username': user_info['username'] if user_info else session.get('username'),
                'model': user_info.get('model', 0) if user_info else 0
            }
        })
    else:
        return create_response(True, data={'authenticated': False}) 