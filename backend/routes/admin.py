"""
管理员相关的路由模块
"""
import logging
import os
import random
import string

from flask import Blueprint, request, session
from werkzeug.exceptions import BadRequest, NotFound

from backend.routes.practice import cache_manager as practice_cache_manager
from ..config import SHEET_NAME
from ..connectDB import (
    get_all_subjects, create_subject, update_subject, delete_subject,
    get_tiku_by_subject, create_or_update_tiku, delete_tiku, toggle_tiku_status,
    create_invitation_code, delete_questions_by_tiku,
    parse_excel_to_questions, insert_questions_batch, toggle_user_status, update_user_model,
    delete_invitation_code, get_system_stats, get_users_paginated,
    get_all_invitations_detailed, get_detailed_question_stats,
    get_question_details_by_id, create_question_and_update_tiku_count,
    update_question_details, delete_question_and_update_tiku_count,
    toggle_question_status_and_update_tiku_count, get_questions_paginated,
    reset_user_password
)
from ..decorators import handle_api_error, login_required, admin_required, permission_cache
from ..utils import (
    create_response,
    ensure_subject_directory,
    remove_file_safely,
    save_uploaded_file,
    get_file_hash,
    load_questions_from_excel
)

logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/stats', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_stats():
    """获取系统统计信息"""
    stats = get_system_stats()
    return create_response(True, data={'stats': stats})


@admin_bp.route('/users', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_users():
    """获取用户列表"""
    # 获取查询参数
    search = request.args.get('search', '').strip()
    order_by = request.args.get('order_by', 'id')
    order_dir = request.args.get('order_dir', 'desc')
    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(10, int(request.args.get('per_page', 20))))

    # Database logic is now in connectDB.get_users_paginated
    result = get_users_paginated(search, order_by, order_dir, page, per_page)

    return create_response(True, data={
        'users': result['users'],
        'pagination': result['pagination']
    })


@admin_bp.route('/invitations', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_invitations():
    """获取邀请码列表"""
    # Database logic is now in connectDB.get_all_invitations_detailed
    invitations = get_all_invitations_detailed()
    return create_response(True, data={'invitations': invitations})


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
            code = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        # 验证邀请码格式
        if not code or len(code) < 6 or len(code) > 64:
            raise BadRequest("邀请码长度必须在6-64个字符之间")

        # 处理过期天数参数
        expire_days_processed = expire_days  # 保存原始值
        if expire_days is not None:
            try:
                # 尝试转换为整数
                if isinstance(expire_days, str):
                    if expire_days.strip() == '':
                        expire_days_processed = None
                    else:
                        expire_days_processed = int(expire_days.strip())
                else:
                    expire_days_processed = int(expire_days)

                # 验证天数范围
                if expire_days_processed is not None and (expire_days_processed <= 0 or expire_days_processed > 3650):
                    raise BadRequest("过期天数必须在1-3650天之间")

            except (ValueError, TypeError):
                raise BadRequest("过期天数必须是有效的整数")

        result = create_invitation_code(code, expire_days_processed)
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
            ensure_subject_directory(subject_name)
            logger.info(f"管理员创建科目: {subject_name}")
            practice_cache_manager.refresh_all_cache()
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
        practice_cache_manager.refresh_all_cache()
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
        for file_path in result.get('deleted_files', []):
            remove_file_safely(file_path)

        practice_cache_manager.refresh_all_cache()
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
        questions = load_questions_from_excel(temp_filepath, SHEET_NAME)
        if questions is None:
            remove_file_safely(temp_filepath)
            raise BadRequest('文件格式错误或无法解析')

        if not questions:
            remove_file_safely(temp_filepath)
            raise BadRequest('文件中没有有效的题目数据')

        # 计算文件信息
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
        practice_cache_manager.refresh_all_cache()
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
            remove_file_safely(file_path)
        practice_cache_manager.refresh_all_cache()
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

    practice_cache_manager.refresh_all_cache()
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
    tiku_id_str = request.args.get('tiku_id')
    tiku_id = None
    if tiku_id_str:
        try:
            tiku_id = int(tiku_id_str)
        except ValueError:
            raise BadRequest('无效的题库ID')

    page = max(1, int(request.args.get('page', 1)))
    per_page = min(100, max(10, int(request.args.get('per_page', 20))))

    # Call the new function in connectDB.py
    result = get_questions_paginated(tiku_id, page, per_page)

    # The data from get_questions_paginated is already in the desired format for the response
    # (a dict with 'questions' list and 'pagination' info).
    # However, the original `get_questions_by_tiku` in connectDB.py (which this route used to call indirectly)
    # had specific formatting for question objects (e.g., 'type' name, 'options_for_practice', 'id' with 'db_' prefix).
    # The new `get_questions_paginated` returns raw DB rows. We need to re-apply that formatting here.

    formatted_questions = []
    for q_row in result['questions']:
        # This formatting logic is adapted from connectDB.get_questions_by_tiku
        options_for_practice = {}
        if q_row.get('option_a'): options_for_practice['A'] = q_row['option_a']
        if q_row.get('option_b'): options_for_practice['B'] = q_row['option_b']
        if q_row.get('option_c'): options_for_practice['C'] = q_row['option_c']
        if q_row.get('option_d'): options_for_practice['D'] = q_row['option_d']

        question_type_code = q_row['question_type']
        type_name = '未知题型'
        is_multiple_choice = False
        if question_type_code == 0:  # Assuming 0: Single
            type_name = '单选题'
        elif question_type_code == 5:  # Assuming 5: Multiple
            type_name = '多选题'
            is_multiple_choice = True
        elif question_type_code == 10:  # Assuming 10: True/False
            type_name = '判断题'
            options_for_practice = None  # Judgment questions don't need options A, B, C, D

        formatted_questions.append({
            'id': f"db_{q_row['id']}",  # Add 'db_' prefix as in original function
            'db_id': q_row['id'],
            'subject_id': q_row['subject_id'],
            'tiku_id': q_row['tiku_id'],
            'type': type_name,
            'question': q_row['stem'],
            'options_for_practice': options_for_practice,
            'answer': q_row['answer'],
            'is_multiple_choice': is_multiple_choice,
            'explanation': q_row['explanation'],
            'difficulty': q_row['difficulty'],
            'status': q_row['status'],
            # This field was not in the original get_questions_by_tiku output structure directly in questions list
            'subject_name': q_row['subject_name'],
            'tiku_name': q_row['tiku_name']
        })

    return create_response(True, data={
        'questions': formatted_questions,
        'pagination': result['pagination']
    })


@admin_bp.route('/questions/stats', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_questions_stats():
    """获取题目统计信息"""
    # Database logic is now in connectDB.get_detailed_question_stats
    stats = get_detailed_question_stats()
    return create_response(True, data=stats)


@admin_bp.route('/reload-banks', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_reload_banks():
    """重新加载题库缓存"""
    try:
        result = practice_cache_manager.refresh_all_cache()
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


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_reset_user_password(user_id):
    """重置用户密码"""
    try:
        data = request.get_json()
        if not data or 'new_password' not in data:
            raise BadRequest("缺少新密码参数")

        new_password = data['new_password'].strip()
        if not new_password:
            raise BadRequest("新密码不能为空")

        if len(new_password) < 6:
            raise BadRequest("密码长度至少6位")

        if len(new_password) > 64:
            raise BadRequest("密码长度不能超过64位")

        # 不能操作自己
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            raise BadRequest("不能重置自己的密码")

        # 调用connectDB中的函数
        result = reset_user_password(user_id, new_password)

        if result['success']:
            logger.info(f"管理员重置用户密码: user_id={user_id}, username={result['username']}")
            return create_response(True, result['message'], data={
                'user_id': result['user_id'],
                'username': result['username']
            })
        else:
            raise BadRequest(result['error'])

    except Exception as e:
        logger.error(f"Error resetting user password {user_id}: {e}")
        raise


# 题目详细管理API
@admin_bp.route('/questions/<int:question_id>', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_question_detail(question_id):
    """获取单个题目详情"""
    question_data = get_question_details_by_id(question_id)
    if not question_data:
        raise NotFound('题目不存在')
    return create_response(True, data={'question': question_data})


@admin_bp.route('/questions', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_create_question():
    """新增题目"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    # 验证必填字段
    required_fields = ['tiku_id', 'question_type', 'stem', 'answer']
    for field in required_fields:
        if field not in data or (isinstance(data[field], str) and not data[field].strip()) or (
                not isinstance(data[field], str) and data[field] is None):
            raise BadRequest(f"缺少或无效的必填字段: {field}")

    # 验证题目类型（支持字符串格式）
    question_type = data['question_type']
    if isinstance(question_type, str):
        if question_type not in ['单选题', '多选题', '判断题']:
            raise BadRequest("无效的题目类型，必须是：单选题、多选题、判断题")
    elif isinstance(question_type, int):
        if question_type not in [0, 5, 10]:
            raise BadRequest("无效的题目类型")
    else:
        raise BadRequest("题目类型格式错误")

    # 验证选项（根据题目类型）
    if question_type in ['单选题', '多选题', 0, 5]:
        # 检查options字典格式
        if 'options' in data and isinstance(data['options'], dict):
            options = data['options']
            if not options.get('A') or not options.get('B'):
                raise BadRequest("单选题和多选题至少需要选项A和B")
        # 检查单独字段格式
        elif not data.get('option_a') or not data.get('option_b'):
            raise BadRequest("单选题和多选题至少需要选项A和B")

    # 验证答案格式
    answer = data.get('answer', '').strip().upper()
    if not answer:
        raise BadRequest("答案不能为空")

    # 根据题目类型验证答案
    if question_type in ['单选题', 0]:
        if answer not in ['A', 'B', 'C', 'D']:
            raise BadRequest("单选题答案必须是A、B、C、D中的一个")
    elif question_type in ['多选题', 5]:
        if not all(c in 'ABCD' for c in answer):
            raise BadRequest("多选题答案必须是A、B、C、D的组合")
    elif question_type in ['判断题', 10]:
        if answer not in ['A', 'B']:
            raise BadRequest("判断题答案必须是A(正确)或B(错误)")

    # 验证难度等级
    difficulty = data.get('difficulty', 1)
    if difficulty not in [1, 2, 3, 4, 5]:
        raise BadRequest("难度等级必须是1-5之间的整数")

    # 验证状态
    status = data.get('status', 'active')
    if status not in ['active', 'inactive']:
        raise BadRequest("状态必须是active或inactive")

    # 调用数据库创建函数
    result = create_question_and_update_tiku_count(data)

    if result['success']:
        logger.info(f"管理员新增题目: question_id={result['question_id']}, tiku_id={data['tiku_id']}")
        # 刷新缓存
        try:
            practice_cache_manager.refresh_all_cache()
            logger.info(f"管理员新增题目: question_id={result['question_id']}, 缓存已刷新")
        except Exception as e:
            logger.warning(f"刷新缓存失败: {e}")

        return create_response(True, result['message'], data={'question_id': result['question_id']})
    else:
        raise BadRequest(result.get('error', "创建题目失败"))


@admin_bp.route('/questions/<int:question_id>', methods=['PUT'])
@login_required
@admin_required
@handle_api_error
def api_admin_update_question(question_id):
    """更新题目"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    # 验证必填字段
    required_fields = ['question_type', 'stem', 'answer']
    for field in required_fields:
        if field not in data or (isinstance(data[field], str) and not data[field].strip()) or (
                not isinstance(data[field], str) and data[field] is None):
            raise BadRequest(f"缺少或无效的必填字段: {field}")

    # 验证题目类型（支持字符串格式）
    question_type = data['question_type']
    if isinstance(question_type, str):
        if question_type not in ['单选题', '多选题', '判断题']:
            raise BadRequest("无效的题目类型，必须是：单选题、多选题、判断题")
    elif isinstance(question_type, int):
        if question_type not in [0, 5, 10]:
            raise BadRequest("无效的题目类型")
    else:
        raise BadRequest("题目类型格式错误")

    # 验证选项（根据题目类型）
    if question_type in ['单选题', '多选题', 0, 5]:
        # 检查options字典格式
        if 'options' in data and isinstance(data['options'], dict):
            options = data['options']
            if not options.get('A') or not options.get('B'):
                raise BadRequest("单选题和多选题至少需要选项A和B")
        # 检查单独字段格式
        elif not data.get('option_a') or not data.get('option_b'):
            raise BadRequest("单选题和多选题至少需要选项A和B")

    # 验证答案格式
    answer = data.get('answer', '').strip().upper()
    if not answer:
        raise BadRequest("答案不能为空")

    # 根据题目类型验证答案
    if question_type in ['单选题', 0]:
        if answer not in ['A', 'B', 'C', 'D']:
            raise BadRequest("单选题答案必须是A、B、C、D中的一个")
    elif question_type in ['多选题', 5]:
        if not all(c in 'ABCD' for c in answer):
            raise BadRequest("多选题答案必须是A、B、C、D的组合")
    elif question_type in ['判断题', 10]:
        if answer not in ['A', 'B']:
            raise BadRequest("判断题答案必须是A(正确)或B(错误)")

    # 验证难度等级
    difficulty = data.get('difficulty', 1)
    if difficulty not in [1, 2, 3, 4, 5]:
        raise BadRequest("难度等级必须是1-5之间的整数")

    # 验证状态
    status = data.get('status', 'active')
    if status not in ['active', 'inactive']:
        raise BadRequest("状态必须是active或inactive")

    # 准备更新数据 - 统一处理
    update_data = {
        'question_type': question_type,
        'stem': data['stem'].strip(),
        'answer': answer,
        'explanation': data.get('explanation', '').strip(),
        'difficulty': difficulty,
        'status': status
    }

    # 处理选项数据
    if 'options' in data and isinstance(data['options'], dict):
        # 前端发送的是options字典格式
        update_data['options'] = data['options']
    else:
        # 前端发送的是单独字段格式，转换为options字典
        if question_type in ['单选题', '多选题', 0, 5]:
            update_data['option_a'] = data.get('option_a', '').strip()
            update_data['option_b'] = data.get('option_b', '').strip()
            update_data['option_c'] = data.get('option_c', '').strip()
            update_data['option_d'] = data.get('option_d', '').strip()

    # 调用数据库更新函数
    result = update_question_details(question_id, update_data)

    if result['success']:
        # 刷新相关缓存
        try:
            # 刷新题目缓存
            practice_cache_manager.refresh_one_question(question_id)
            logger.info(f"管理员更新题目: question_id={question_id}, 缓存已刷新")
        except Exception as e:
            logger.warning(f"刷新缓存失败: {e}")

        logger.info(f"管理员更新题目: question_id={question_id}")
        return create_response(True, result['message'], data={'question_id': question_id})
    else:
        error_message = result.get('error', "更新题目失败")
        if error_message == "题目不存在":
            raise NotFound(error_message)
        else:
            raise BadRequest(error_message)


@admin_bp.route('/questions/<int:question_id>', methods=['DELETE'])
@login_required
@admin_required
@handle_api_error
def api_admin_delete_question(question_id):
    """删除题目"""
    result = delete_question_and_update_tiku_count(question_id)

    if result['success']:
        logger.info(f"管理员删除题目: question_id={question_id}, tiku_id_affected={result.get('tiku_id_affected')}")
        practice_cache_manager.refresh_all_cache()
        return create_response(True, result['message'])
    else:
        error_message = result.get('error', "删除题目失败")
        if error_message == "题目不存在":
            raise NotFound(error_message)
        else:
            raise BadRequest(error_message)


@admin_bp.route('/questions/<int:question_id>/toggle', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_toggle_question_status(question_id):
    """切换题目状态"""
    result = toggle_question_status_and_update_tiku_count(question_id)

    if result['success']:
        action = "启用" if result['status'] == 'active' else "禁用"
        logger.info(f"管理员{action}题目: question_id={question_id}, tiku_id_affected={result.get('tiku_id_affected')}")
        practice_cache_manager.refresh_all_cache()
        return create_response(True, result['message'], data={'status': result['status']})
    else:
        error_message = result.get('error', "切换题目状态失败")
        if error_message == "题目不存在":
            raise NotFound(error_message)
        else:
            raise BadRequest(error_message)
