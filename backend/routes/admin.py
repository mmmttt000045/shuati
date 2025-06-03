"""
管理员相关的路由模块
"""
import logging
from flask import Blueprint, request
from werkzeug.exceptions import BadRequest, NotFound

from ..decorators import handle_api_error, login_required, admin_required
from ..utils import create_response
from ..connectDB import (
    get_all_subjects, create_subject, update_subject, delete_subject,
    get_tiku_by_subject, create_or_update_tiku, delete_tiku, toggle_tiku_status,
    create_invitation_code, get_questions_by_tiku, delete_questions_by_tiku,
    parse_excel_to_questions, insert_questions_batch, toggle_user_status, update_user_model
)
from backend.routes.practice import refresh_all_cache_from_mysql

logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_stats():
    """获取系统统计信息"""
    try:
        from ..connectDB import get_db_connection

        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")

        cursor = connection.cursor()

        # 用户统计
        cursor.execute("SELECT COUNT(*) FROM user_accounts")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_accounts WHERE is_enabled = TRUE")
        active_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_accounts WHERE model = 10")
        admin_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM user_accounts WHERE model = 5")
        vip_users = cursor.fetchone()[0]

        # 邀请码统计
        cursor.execute("SELECT COUNT(*) FROM invitation_codes")
        total_invitations = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM invitation_codes WHERE is_used = FALSE AND (expires_at IS NULL OR expires_at > NOW())")
        unused_invitations = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM invitation_codes WHERE is_used = TRUE")
        used_invitations = cursor.fetchone()[0]

        # 题库统计
        cursor.execute("SELECT COUNT(*) FROM questions WHERE status = 'active'")
        total_questions = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tiku WHERE is_active = 1")
        total_files = cursor.fetchone()[0]

        stats = {
            'users': {
                'total': total_users,
                'active': active_users,
                'admins': admin_users,
                'vips': vip_users
            },
            'invitations': {
                'total': total_invitations,
                'unused': unused_invitations,
                'used': used_invitations
            },
            'subjects': {
                'total_questions': total_questions,
                'total_files': total_files
            }
        }

        return create_response(True, data={'stats': stats})

    except Exception as e:
        logger.error(f"Error getting admin stats: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_users():
    """获取用户列表"""
    try:
        from ..connectDB import get_db_connection

        # 获取查询参数
        search = request.args.get('search', '').strip()
        order_by = request.args.get('order_by', 'id')
        order_dir = request.args.get('order_dir', 'desc')
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(10, int(request.args.get('per_page', 20))))

        # 验证排序字段
        valid_order_fields = ['id', 'username', 'created_at', 'last_time_login', 'model']
        if order_by not in valid_order_fields:
            order_by = 'id'

        # 验证排序方向
        if order_dir.lower() not in ['asc', 'desc']:
            order_dir = 'desc'

        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")

        cursor = connection.cursor()

        # 构建查询条件
        where_conditions = []
        query_params = []

        if search:
            where_conditions.append("u.username LIKE %s")
            query_params.append(f"%{search}%")

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        # 计算总数
        count_query = f"""
        SELECT COUNT(*) as total
        FROM user_accounts u
        {where_clause}
        """
        cursor.execute(count_query, query_params)
        total_count = cursor.fetchone()[0]

        # 计算分页信息
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page

        # 获取用户列表
        query = f"""
        SELECT 
            u.id, u.username, u.is_enabled, u.created_at, u.last_time_login, u.model,
            i.code as invitation_code
        FROM user_accounts u
        LEFT JOIN invitation_codes i ON u.used_invitation_code_id = i.id
        {where_clause}
        ORDER BY u.{order_by} {order_dir.upper()}
        LIMIT %s OFFSET %s
        """
        cursor.execute(query, query_params + [per_page, offset])
        users_data = cursor.fetchall()

        users = []
        for user_data in users_data:
            user_id, username, is_enabled, created_at, last_login, model, invitation_code = user_data
            users.append({
                'id': user_id,
                'username': username,
                'is_enabled': bool(is_enabled),
                'created_at': created_at.isoformat() if created_at else None,
                'last_time_login': last_login.isoformat() if last_login else None,
                'model': model if model is not None else 0,
                'invitation_code': invitation_code
            })

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }

        return create_response(True, data={
            'users': users,
            'pagination': pagination
        })

    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@admin_bp.route('/invitations', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_invitations():
    """获取邀请码列表"""
    try:
        from ..connectDB import get_db_connection

        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")

        cursor = connection.cursor()

        query = """
                SELECT i.id,
                       i.code,
                       i.is_used,
                       i.created_at,
                       i.expires_at,
                       i.used_time,
                       u.username as used_by_username
                FROM invitation_codes i
                         LEFT JOIN user_accounts u ON i.used_by_user_id = u.id
                ORDER BY i.created_at DESC
                """
        cursor.execute(query)
        invitations_data = cursor.fetchall()

        invitations = []
        for invitation_data in invitations_data:
            inv_id, code, is_used, created_at, expires_at, used_time, used_by_username = invitation_data
            invitations.append({
                'id': inv_id,
                'code': code,
                'is_used': bool(is_used),
                'created_at': created_at.isoformat() if created_at else None,
                'expires_at': expires_at.isoformat() if expires_at else None,
                'used_time': used_time.isoformat() if used_time else None,
                'used_by_username': used_by_username
            })

        return create_response(True, data={'invitations': invitations})

    except Exception as e:
        logger.error(f"Error getting invitations: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@admin_bp.route('/invitations', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_create_invitation():
    """创建邀请码"""
    try:
        data = request.get_json() or {}
        code = data.get('code', '').strip()
        expire_days = data.get('expire_days')

        # 如果没有提供邀请码，生成一个
        if not code:
            import random
            import string
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        # 验证邀请码格式
        if not code or len(code) < 6 or len(code) > 64:
            raise BadRequest("邀请码长度必须在6-64个字符之间")

        # 处理过期天数参数
        if expire_days is not None:
            try:
                # 尝试转换为整数
                if isinstance(expire_days, str):
                    if expire_days.strip() == '':
                        expires_days = None
                    else:
                        expires_days = int(expire_days.strip())
                else:
                    expires_days = int(expire_days)
                
                # 验证天数范围
                if expires_days is not None and (expires_days <= 0 or expires_days > 3650):
                    raise BadRequest("过期天数必须在1-3650天之间")
                    
            except (ValueError, TypeError):
                raise BadRequest("过期天数必须是有效的整数")

        result = create_invitation_code(code, expires_days)
        if result['success']:
            return create_response(True, result['message'], data={'invitation_code': result['code']})
        else:
            raise BadRequest(result['error'])

    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise

@admin_bp.route('/invitations/<int:invitation_id>', methods=['DELETE'])
@login_required
@admin_required
@handle_api_error
def api_admin_delete_invitation(invitation_id):
    """删除未使用的邀请码"""
    try:
        from ..connectDB import delete_invitation_code
        result = delete_invitation_code(invitation_id)

        if result['success']:
            logger.info(f"管理员删除邀请码: {result.get('deleted_code', invitation_id)}")
            return create_response(True, result['message'])
        else:
            raise BadRequest(result['error'])

    except Exception as e:
        logger.error(f"Error deleting invitation: {e}")
        raise


# 科目管理API
@admin_bp.route('/subjects', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_subjects():
    """获取所有科目"""
    subjects = get_all_subjects()
    return create_response(True, data={'subjects': subjects})


@admin_bp.route('/subjects', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_create_subject():
    """创建新科目"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    subject_name = data.get('subject_name', '').strip()
    if not subject_name:
        raise BadRequest('科目名称不能为空')

    if len(subject_name) > 50:
        raise BadRequest('科目名称不能超过50个字符')

    exam_time = data.get('exam_time', '').strip()
    if exam_time == '':
        exam_time = None

    result = create_subject(subject_name, exam_time)
    if result['success']:
        # 创建对应的文件系统目录
        try:
            from ..utils import ensure_subject_directory
            ensure_subject_directory(subject_name)
            logger.info(f"管理员创建科目: {subject_name}")
            refresh_all_cache_from_mysql()  # 刷新缓存
            return create_response(True, result['message'], data={'subject_id': result['subject_id']})
        except Exception as e:
            # 如果目录创建失败，尝试删除数据库记录
            delete_subject(result['subject_id'])
            raise Exception(f"创建科目目录失败: {e}")
    else:
        raise BadRequest(result['error'])


@admin_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
@login_required
@admin_required
@handle_api_error
def api_admin_update_subject(subject_id):
    """更新科目信息"""
    data = request.get_json()
    if not data:
        raise BadRequest('缺少请求数据')

    subject_name = data.get('subject_name', '').strip()
    if not subject_name:
        raise BadRequest('科目名称不能为空')

    if len(subject_name) > 50:
        raise BadRequest('科目名称不能超过50个字符')

    exam_time = data.get('exam_time', '').strip()
    if exam_time == '':
        exam_time = None

    result = update_subject(subject_id, subject_name, exam_time)
    if result['success']:
        refresh_all_cache_from_mysql()  # 刷新缓存
        logger.info(f"管理员更新科目: {subject_id} -> {subject_name}")
        return create_response(True, result['message'])
    else:
        raise BadRequest(result['error'])


@admin_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
@login_required
@admin_required
@handle_api_error
def api_admin_delete_subject(subject_id):
    """删除科目"""
    result = delete_subject(subject_id)
    if result['success']:
        # 删除对应的文件
        from ..utils import remove_file_safely
        for file_path in result.get('deleted_files', []):
            remove_file_safely(file_path)

        refresh_all_cache_from_mysql()  # 刷新缓存
        logger.info(f"管理员删除科目: {subject_id}")
        return create_response(True, result['message'])
    else:
        raise BadRequest(result['error'])


# 题库管理API
@admin_bp.route('/tiku', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_tiku():
    """获取题库列表"""
    subject_id = request.args.get('subject_id')
    if subject_id:
        try:
            subject_id = int(subject_id)
        except ValueError:
            raise BadRequest('无效的科目ID')

    tiku_list = get_tiku_by_subject(subject_id)
    return create_response(True, data={'tiku_list': tiku_list})


@admin_bp.route('/tiku/upload', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_upload_tiku():
    """上传题库文件"""
    from ..utils import save_uploaded_file, remove_file_safely, get_file_hash

    if 'file' not in request.files:
        raise BadRequest('没有上传文件')

    file = request.files['file']
    if file.filename == '':
        raise BadRequest('没有选择文件')

    subject_id = request.form.get('subject_id')
    tiku_name = request.form.get('tiku_name', '').strip()

    if not subject_id:
        raise BadRequest('缺少科目ID')

    try:
        subject_id = int(subject_id)
    except ValueError:
        raise BadRequest('无效的科目ID')

    if not tiku_name:
        # 如果没有提供题库名称，使用文件名
        tiku_name = file.filename.replace('.xlsx', '').replace('.xls', '')

    # 验证文件类型
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise BadRequest('只支持Excel文件 (.xlsx, .xls)')

    # 获取科目信息
    subjects = get_all_subjects()
    subject_map = {s['subject_id']: s['subject_name'] for s in subjects}

    if subject_id not in subject_map:
        raise BadRequest('科目不存在')

    subject_name = subject_map[subject_id]

    try:
        # 保存临时文件用于解析
        temp_filepath = save_uploaded_file(file, subject_name, tiku_name)

        # 解析Excel文件
        from ..data_loader import load_questions_from_excel
        from ..config import SHEET_NAME
        questions = load_questions_from_excel(temp_filepath, SHEET_NAME)
        if questions is None:
            remove_file_safely(temp_filepath)
            raise BadRequest('文件格式错误或无法解析')

        if not questions:
            remove_file_safely(temp_filepath)
            raise BadRequest('文件中没有有效的题目数据')

        # 计算文件信息
        import os
        file_size = os.path.getsize(temp_filepath)
        file_hash = get_file_hash(temp_filepath)

        # 创建题库记录
        result = create_or_update_tiku(
            subject_id=subject_id,
            tiku_name=tiku_name,
            tiku_position=temp_filepath,
            tiku_nums=len(questions),
            file_size=file_size,
            file_hash=file_hash
        )

        if not result['success']:
            remove_file_safely(temp_filepath)
            raise BadRequest(result['error'])

        tiku_id = result['tiku_id']

        # 删除该题库的旧题目（如果存在）
        delete_questions_by_tiku(tiku_id)

        # 将解析的题目转换为数据库格式
        db_questions = parse_excel_to_questions(subject_id, tiku_id, questions)

        # 批量插入题目到数据库
        insert_result = insert_questions_batch(db_questions)
        if not insert_result['success']:
            # 如果插入失败，删除题库记录和文件
            delete_tiku(tiku_id)
            remove_file_safely(temp_filepath)
            raise BadRequest(f"插入题目失败: {insert_result['error']}")

        # 更新题库记录中的题目数量（以数据库中实际插入的为准）
        actual_count = insert_result['inserted_count']
        if actual_count != len(questions):
            logger.warning(f"题库 {tiku_name}: 解析{len(questions)}题，实际插入{actual_count}题")
            # 更新题库记录
            create_or_update_tiku(
                subject_id=subject_id,
                tiku_name=tiku_name,
                tiku_position=temp_filepath,
                tiku_nums=actual_count,
                file_size=file_size,
                file_hash=file_hash
            )

        logger.info(f"管理员上传题库: {tiku_name} (解析{len(questions)}题，插入{actual_count}题)")
        refresh_all_cache_from_mysql()  # 刷新缓存
        return create_response(True, f"题库上传成功，共{actual_count}道题目", data={
            'tiku_id': tiku_id,
            'question_count': actual_count,
            'file_path': temp_filepath
        })

    except Exception as e:
        logger.error(f"上传题库失败: {e}")
        raise


@admin_bp.route('/tiku/<int:tiku_id>', methods=['DELETE'])
@login_required
@admin_required
@handle_api_error
def api_admin_delete_tiku(tiku_id):
    """删除题库"""
    # 先删除题库中的所有题目
    delete_result = delete_questions_by_tiku(tiku_id)
    if not delete_result['success']:
        logger.warning(f"删除题库题目失败: {delete_result['error']}")

    # 删除题库记录
    result = delete_tiku(tiku_id)
    if result['success']:
        # 删除文件
        file_path = result.get('file_path')
        if file_path:
            from ..utils import remove_file_safely
            remove_file_safely(file_path)
        refresh_all_cache_from_mysql()  # 刷新缓存
        logger.info(f"管理员删除题库: {tiku_id}")
        return create_response(True, result['message'])
    else:
        raise BadRequest(result['error'])


@admin_bp.route('/tiku/<int:tiku_id>/toggle', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_toggle_tiku(tiku_id):
    """切换题库启用状态"""
    result = toggle_tiku_status(tiku_id)

    refresh_all_cache_from_mysql()  # 刷新缓存
    if result['success']:
        logger.info(f"管理员切换题库状态: {tiku_id} -> {'启用' if result['is_active'] else '禁用'}")
        return create_response(True, result['message'], data={'is_active': result['is_active']})
    else:
        raise BadRequest(result['error'])


@admin_bp.route('/questions', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_questions():
    """获取题目列表"""
    try:
        tiku_id = request.args.get('tiku_id')
        page = max(1, int(request.args.get('page', 1)))
        per_page = min(100, max(10, int(request.args.get('per_page', 20))))

        if tiku_id:
            try:
                tiku_id = int(tiku_id)
                questions = get_questions_by_tiku(tiku_id)
            except ValueError:
                raise BadRequest('无效的题库ID')
        else:
            questions = get_questions_by_tiku()

        # 简单的内存分页
        total_count = len(questions)
        total_pages = (total_count + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_questions = questions[start_idx:end_idx]

        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total_count,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }

        return create_response(True, data={
            'questions': page_questions,
            'pagination': pagination
        })

    except Exception as e:
        logger.error(f"获取题目列表失败: {e}")
        raise


@admin_bp.route('/questions/stats', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_questions_stats():
    """获取题目统计信息"""
    try:
        from ..connectDB import get_db_connection

        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")

        cursor = connection.cursor()

        # 题目总数统计
        cursor.execute("SELECT COUNT(*) FROM questions WHERE status = 'active'")
        total_questions = cursor.fetchone()[0]

        # 按题型统计
        cursor.execute("""
                       SELECT question_type, COUNT(*) as count
                       FROM questions
                       WHERE status = 'active'
                       GROUP BY question_type
                       """)
        type_stats = []
        type_names = {0: '单选题', 5: '多选题', 10: '判断题'}
        for row in cursor.fetchall():
            question_type, count = row
            type_stats.append({
                'type': type_names.get(question_type, f'类型{question_type}'),
                'type_code': question_type,
                'count': count
            })

        # 按科目统计
        cursor.execute("""
                       SELECT s.subject_name, COUNT(q.id) as count
                       FROM subject s
                           LEFT JOIN questions q
                       ON s.subject_id = q.subject_id AND q.status = 'active'
                       GROUP BY s.subject_id, s.subject_name
                       ORDER BY count DESC
                       """)
        subject_stats = []
        for row in cursor.fetchall():
            subject_name, count = row
            subject_stats.append({
                'subject_name': subject_name,
                'count': count
            })

        # 按题库统计
        cursor.execute("""
                       SELECT t.tiku_name, s.subject_name, COUNT(q.id) as count
                       FROM tiku t
                           LEFT JOIN questions q
                       ON t.tiku_id = q.tiku_id AND q.status = 'active'
                           LEFT JOIN subject s ON t.subject_id = s.subject_id
                       WHERE t.is_active = 1
                       GROUP BY t.tiku_id, t.tiku_name, s.subject_name
                       ORDER BY count DESC
                       """)
        tiku_stats = []
        for row in cursor.fetchall():
            tiku_name, subject_name, count = row
            tiku_stats.append({
                'tiku_name': tiku_name,
                'subject_name': subject_name,
                'count': count
            })

        return create_response(True, data={
            'total_questions': total_questions,
            'type_stats': type_stats,
            'subject_stats': subject_stats,
            'tiku_stats': tiku_stats
        })

    except Exception as e:
        logger.error(f"获取题目统计失败: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@admin_bp.route('/reload-banks', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_reload_banks():
    """重新加载题库缓存"""
    try:
        result = refresh_all_cache_from_mysql()
        return create_response(True, result['message'], {
            'tiku_count': result['tiku_count'],
            'subjects_count': result['subjects_count']
        })
    except Exception as e:
        logger.error(f"重新加载题库缓存失败: {e}")
        return create_response(False, f'重新加载题库缓存失败: {str(e)}', status_code=500)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_toggle_user(user_id):
    """启用/禁用用户"""
    try:
        from flask import session

        # 不能操作自己
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            raise BadRequest("不能操作自己的账户")

        # 调用connectDB中的函数
        result = toggle_user_status(user_id)

        if result['success']:
            action = "启用" if result['is_enabled'] else "禁用"
            logger.info(f"管理员{action}用户: user_id={user_id}, username={result['username']}")
            return create_response(True, result['message'], data={'is_enabled': result['is_enabled']})
        else:
            raise BadRequest(result['error'])

    except Exception as e:
        logger.error(f"Error toggling user {user_id}: {e}")
        raise


@admin_bp.route('/users/<int:user_id>/model', methods=['PUT'])
@login_required
@admin_required
@handle_api_error
def api_admin_update_user_model(user_id):
    """更新用户权限模型"""
    try:
        from ..decorators import permission_cache
        from flask import session

        data = request.get_json()
        if not data or 'model' not in data:
            raise BadRequest("缺少模型参数")

        model = data['model']
        if model not in [0, 5, 10]:
            raise BadRequest("无效的用户模型")

        # 不能操作自己
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            raise BadRequest("不能修改自己的权限")

        # 调用connectDB中的函数
        result = update_user_model(user_id, model)

        if result['success']:
            # 更新缓存
            permission_cache.update_user_model(user_id, model)

            logger.info(f"管理员更新用户权限: user_id={user_id}, username={result['username']}, model={model}")
            return create_response(True, result['message'], data={
                'model': result['model'],
                'user_id': result['user_id'],
                'username': result['username']
            })
        else:
            raise BadRequest(result['error'])

    except Exception as e:
        logger.error(f"Error updating user model {user_id}: {e}")
        raise
