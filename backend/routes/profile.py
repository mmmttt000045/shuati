"""
用户个人资料相关的路由模块
"""
import logging

from flask import Blueprint, request, session
from werkzeug.exceptions import BadRequest, NotFound

from ..connectDB import (
    hash_password, with_db_connection
)
from ..config import SESSION_KEYS
from ..decorators import handle_api_error, login_required
from ..utils import create_response

logger = logging.getLogger(__name__)

# 创建蓝图
profile_bp = Blueprint('profile', __name__, url_prefix='/api/profile')


@with_db_connection
def get_user_detailed_info(cursor, user_id: int):
    """获取用户详细信息，包括扩展字段"""
    query = """
            SELECT id,
                   username,
                   is_enabled,
                   created_at,
                   last_time_login,
                   model,
                   email,
                   student_id,
                   major,
                   grade
            FROM user_accounts
            WHERE id = %s
            """
    cursor.execute(query, (user_id,))
    return cursor.fetchone()


@with_db_connection
def update_user_profile(cursor, user_id: int, update_data: dict):
    """更新用户个人资料"""
    # 构建动态更新查询
    allowed_fields = ['username', 'email', 'student_id', 'major', 'grade']
    update_fields = []
    update_values = []

    for field, value in update_data.items():
        if field in allowed_fields:
            update_fields.append(f"{field} = %s")
            update_values.append(value)

    if not update_fields:
        return {"success": False, "error": "没有有效的更新字段"}

    # 检查用户名是否已被其他用户使用
    if 'username' in update_data:
        cursor.execute("SELECT id FROM user_accounts WHERE username = %s AND id != %s",
                       (update_data['username'], user_id))
        if cursor.fetchone():
            return {"success": False, "error": "用户名已被占用"}

    # 执行更新
    update_values.append(user_id)
    query = f"UPDATE user_accounts SET {', '.join(update_fields)} WHERE id = %s"
    cursor.execute(query, update_values)

    if cursor.rowcount == 0:
        return {"success": False, "error": "用户不存在或更新失败"}

    return {"success": True, "message": "个人信息更新成功"}


@with_db_connection
def change_user_password(cursor, user_id: int, current_password: str, new_password: str):
    """修改用户密码"""
    # 验证当前密码
    cursor.execute("SELECT password_hash FROM user_accounts WHERE id = %s", (user_id,))
    user_record = cursor.fetchone()

    if not user_record:
        return {"success": False, "error": "用户不存在"}

    current_password_hash = hash_password(current_password)
    if user_record['password_hash'] != current_password_hash:
        return {"success": False, "error": "当前密码不正确"}

    # 更新密码
    new_password_hash = hash_password(new_password)
    cursor.execute("UPDATE user_accounts SET password_hash = %s WHERE id = %s",
                   (new_password_hash, user_id))

    if cursor.rowcount == 0:
        return {"success": False, "error": "密码更新失败"}

    return {"success": True, "message": "密码修改成功"}


@profile_bp.route('/info', methods=['GET'])
@login_required
@handle_api_error
def api_get_profile_info():
    """获取用户详细个人信息"""
    user_id = session.get(SESSION_KEYS['USER_ID'])
    user_info = get_user_detailed_info(user_id)

    if not user_info:
        raise NotFound('用户信息不存在')

    # 格式化返回数据
    profile_data = {
        'id': user_info['id'],
        'username': user_info['username'],
        'email': user_info.get('email'),
        'student_id': user_info.get('student_id'),
        'major': user_info.get('major'),
        'grade': user_info.get('grade'),
        'is_enabled': user_info['is_enabled'],
        'created_at': user_info['created_at'].isoformat() if user_info['created_at'] else None,
        'last_time_login': user_info['last_time_login'].isoformat() if user_info.get('last_time_login') else None,
        'model': user_info.get('model', 0)
    }

    return create_response(True, data={'user': profile_data})


@profile_bp.route('/info', methods=['PUT'])
@login_required
@handle_api_error
def api_update_profile_info():
    """更新用户个人信息"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    user_id = session.get(SESSION_KEYS['USER_ID'])

    # 验证输入数据
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    student_id = data.get('student_id', '').strip()
    major = data.get('major', '').strip()
    grade = data.get('grade')

    # 构建更新数据
    update_data = {}

    if username:
        if not (3 <= len(username) <= 20):
            raise BadRequest('用户名长度必须在3-100个字符之间')
        update_data['username'] = username

    if email:
        # 简单的邮箱格式验证
        if '@' not in email or '.' not in email.split('@')[-1]:
            raise BadRequest('邮箱格式不正确')
        update_data['email'] = email

    if student_id:
        if len(student_id) > 15:
            raise BadRequest('学号不能超过15个字符')
        update_data['student_id'] = student_id

    if major:
        if len(major) > 30:
            raise BadRequest('专业名称不能超过255个字符')
        update_data['major'] = major

    if grade is not None:
        if not isinstance(grade, int) or not (2020 <= grade <= 2030):
            raise BadRequest('年级必须是2020-2030之间的整数')
        update_data['grade'] = grade

    if not update_data:
        raise BadRequest('没有提供有效的更新数据')

    # 执行更新
    result = update_user_profile(user_id, update_data)

    if result['success']:
        # 如果更新了用户名，需要更新session
        if 'username' in update_data:
            session[SESSION_KEYS['USERNAME']] = update_data['username']
            session.modified = True

        logger.info(f"User {user_id} updated profile: {list(update_data.keys())}")
        return create_response(True, result['message'])
    else:
        raise BadRequest(result['error'])


@profile_bp.route('/password', methods=['PUT'])
@login_required
@handle_api_error
def api_change_password():
    """修改密码"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    current_password = data.get('currentPassword', '').strip()
    new_password = data.get('newPassword', '').strip()
    confirm_password = data.get('confirmPassword', '').strip()

    # 验证输入
    if not all([current_password, new_password, confirm_password]):
        raise BadRequest('当前密码、新密码和确认密码都不能为空')

    if new_password != confirm_password:
        raise BadRequest('两次输入的新密码不一致')

    if len(new_password) < 8:
        raise BadRequest('新密码长度至少8个字符')

    # 检查密码复杂度（至少包含字母和数字）
    has_letter = any(c.isalpha() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    if not (has_letter and has_digit):
        raise BadRequest('密码必须包含字母和数字')

    user_id = session.get(SESSION_KEYS['USER_ID'])
    result = change_user_password(user_id, current_password, new_password)

    if result['success']:
        logger.info(f"User {user_id} changed password successfully")
        return create_response(True, result['message'])
    else:
        raise BadRequest(result['error'])
