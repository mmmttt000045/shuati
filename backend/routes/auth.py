"""
用户认证相关的路由模块
"""
import logging

from flask import Blueprint, request, session
from werkzeug.exceptions import BadRequest, NotFound

from ..config import SESSION_KEYS
from ..connectDB import (
    authenticate_user, create_user, verify_invitation_code,
    get_user_info
)
from ..decorators import handle_api_error, login_required
from ..session_manager import (
    clear_all_session, check_and_resume_practice_session
)
from ..utils import create_response

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
        user_id = result['user_id']

        # 设置session数据，Flask-Session会自动管理
        session[SESSION_KEYS['USER_ID']] = user_id
        session[SESSION_KEYS['USERNAME']] = result['username']
        session[SESSION_KEYS['USER_MODEL']] = result['model']
        session.permanent = True  # 使用永久session，受PERMANENT_SESSION_LIFETIME控制

        # 尝试恢复练习session（如果有的话），但不让它影响登录流程
        try:
            check_and_resume_practice_session(user_id)
        except Exception as e:
            logger.warning(f"恢复练习session失败，但不影响登录: {e}")

        logger.info(f"User logged in: {result['username']}")
        return create_response(True, '登录成功',
                               {
                                   'user': {
                                       'user_id': user_id,
                                       'username': result['username'],
                                       'model': result['model'],
                                       'email': result['email']
                                   },
                                   'session': {
                                       'is_authenticated': True,
                                       'session_valid': True,
                                       'user_id': user_id,
                                       'username': result['username']
                                   }
                               })
    else:
        logger.warning(f"Failed login attempt for username: {username}")
        raise BadRequest(result['error'])


@auth_bp.route('/logout', methods=['POST'])
@handle_api_error
def api_logout():
    """用户登出"""
    if session.get(SESSION_KEYS['USER_ID']):
        username = session.get(SESSION_KEYS['USERNAME'], 'Unknown')
        clear_all_session()
        logger.info(f"User logged out: {username}")
        return create_response(True, '登出成功')
    else:
        raise BadRequest('用户未登录')


@auth_bp.route('/user', methods=['GET'])
@login_required
@handle_api_error
def api_get_user_info():
    """获取当前用户信息"""
    user_id = session.get(SESSION_KEYS['USER_ID'])
    user_info = get_user_info(user_id)

    if user_info:
        return create_response(True, data={
            'user': {
                'user_id': user_info['id'],
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
    user_id = session.get(SESSION_KEYS['USER_ID'])
    if user_id:
        # 获取完整的用户信息，包括身份模型
        user_info = get_user_info(user_id)

        return create_response(True, data={
            'authenticated': True,
            'user': {
                'user_id': user_info['id'] if user_info else user_id,
                'username': user_info['username'] if user_info else session.get(SESSION_KEYS['USERNAME']),
                'model': user_info.get('model', 0) if user_info else 0
            }
        })
    else:
        return create_response(True, data={'authenticated': False})


@auth_bp.route('/session/status', methods=['GET'])
@handle_api_error
def api_session_status():
    """获取session状态信息 - 简化版本"""
    user_id = session.get(SESSION_KEYS['USER_ID'])

    if user_id:
        return create_response(True, data={
            'session': {
                'is_authenticated': True,
                'session_valid': True,
                'user_id': user_id,
                'username': session.get(SESSION_KEYS['USERNAME'])
            },
            'message': 'Session活跃'
        })
    else:
        return create_response(True, data={
            'session': {'is_authenticated': False, 'session_valid': False},
            'message': '用户未登录'
        })


@auth_bp.route('/session/extend', methods=['POST'])
@login_required
@handle_api_error
def api_extend_session():
    """延长session时间 - Flask-Session会自动处理"""
    # Flask-Session在每次请求时会自动更新过期时间（如果SESSION_REFRESH_EACH_REQUEST=True）
    # 这里只需要触碰一下session即可
    session.permanent = True

    logger.debug(f"Session延长请求: user_id={session.get(SESSION_KEYS['USER_ID'])}")

    return create_response(True, '会话时间已延长', data={
        'session': {
            'is_authenticated': True,
            'session_valid': True,
            'user_id': session.get(SESSION_KEYS['USER_ID']),
            'username': session.get(SESSION_KEYS['USERNAME'])
        }
    })


@auth_bp.route('/session/warning-shown', methods=['POST'])
@login_required
@handle_api_error
def api_mark_warning_shown():
    """标记过期警告已显示 - 简化版本"""
    # 在简化的版本中，我们可以选择不实现复杂的警告机制
    # 或者简单地在session中标记
    session['warning_shown'] = True

    return create_response(True, '警告状态已更新')
