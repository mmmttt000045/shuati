"""
练习相关的路由模块
"""
import logging
import random
import time
from flask import Blueprint, request, session, jsonify
from werkzeug.exceptions import BadRequest, NotFound

from ..decorators import handle_api_error, login_required
from ..utils import create_response, format_answer_display, validate_answer
from ..session_manager import (
    get_session_value, set_session_value, clear_practice_session,
    save_session_to_db, get_tiku_position_by_id, get_current_tiku_info
)
from ..config import SESSION_KEYS, QUESTION_STATUS, SUBJECT_DIRECTORY
from ..connectDB import get_questions_by_tiku, get_all_questions_by_tiku_dict
from ..utils import normalize_filepath

from ..connectDB import get_tiku_by_subject, get_all_subjects

logger = logging.getLogger(__name__)

# 创建蓝图
practice_bp = Blueprint('practice', __name__, url_prefix='/api')

# 全局变量，存储题目数据
APP_WIDE_QUESTION_DATA = {}

# 题库使用统计
tiku_usage_stats = {}
import threading

usage_stats_lock = threading.Lock()

# 题库列表缓存（永久缓存，直到手动刷新）
TIKU_LIST_CACHE = {
    'data': None,
    'last_time_reflash': None  # 用于检测原始数据是否变化
}
tiku_cache_lock = threading.Lock()

# 处理后的文件选项缓存（永久缓存，直到手动刷新）
FILE_OPTIONS_CACHE = {
    'data': None,
    'last_time_reflash': None  # 用于检测原始数据是否变化
}
file_options_cache_lock = threading.Lock()


def get_cached_tiku_list():
    """获取缓存的题库列表"""
    with tiku_cache_lock:
        # 如果缓存存在，直接返回
        if TIKU_LIST_CACHE['data'] is not None:
            logger.debug("使用缓存的题库列表数据")
            return TIKU_LIST_CACHE['data']

        # 缓存不存在，从数据库加载
        logger.info("题库列表缓存不存在，从数据库加载")
        try:
            # 获取所有题库和科目信息
            db_tiku_list = get_tiku_by_subject()
            all_subjects = get_all_subjects()
            subjects_exam_time = {s['subject_name']: s['exam_time'] for s in all_subjects}

            # 更新缓存
            TIKU_LIST_CACHE['data'] = {
                'tiku_list': db_tiku_list,
                'subjects_exam_time': subjects_exam_time
            }
            TIKU_LIST_CACHE['last_time_reflash'] = time.time()

            logger.info(f"成功加载并缓存了 {len(db_tiku_list)} 个题库")
            return TIKU_LIST_CACHE['data']

        except Exception as e:
            logger.error(f"从数据库加载题库列表失败: {e}")
            raise


def get_cached_file_options():
    """获取缓存的文件选项数据"""
    with file_options_cache_lock:
        # 如果缓存存在，直接返回
        if FILE_OPTIONS_CACHE['data'] is not None:
            logger.debug("使用缓存的文件选项数据")
            return FILE_OPTIONS_CACHE['data']

        # 缓存不存在，从题库列表缓存构建
        logger.info("文件选项缓存不存在，重新构建")
        try:
            cached_tiku_data = get_cached_tiku_list()
            db_tiku_list = cached_tiku_data['tiku_list']
            subjects_exam_time = cached_tiku_data['subjects_exam_time']

            # 处理题库数据
            db_tiku_map = {}
            for tiku in db_tiku_list:
                if tiku['is_active']:  # 只显示启用的题库
                    subject_name = tiku['subject_name']
                    if subject_name not in db_tiku_map:
                        db_tiku_map[subject_name] = {
                            'files': [],
                            'exam_time': subjects_exam_time.get(subject_name)
                        }

                    db_tiku_map[subject_name]['files'].append({
                        'key': tiku['tiku_position'],
                        'display': tiku['tiku_name'],
                        'count': tiku['tiku_nums'],
                        'file_size': tiku['file_size'],
                        'updated_at': tiku['updated_at'],
                        'tiku_id': tiku['tiku_id']
                        # 注意：progress 字段不在这里缓存，需要动态添加
                    })

            # 排序处理
            sorted_subjects = {}
            for subject, data in sorted(db_tiku_map.items()):
                sorted_subjects[subject] = {
                    'files': sorted(data['files'], key=lambda x: x['display']),
                    'exam_time': data['exam_time']
                }

            # 更新缓存
            FILE_OPTIONS_CACHE['data'] = sorted_subjects

            FILE_OPTIONS_CACHE['last_time_reflash'] = time.time()

            logger.info(f"成功处理并缓存了 {len(sorted_subjects)} 个科目的文件选项")
            return sorted_subjects

        except Exception as e:
            logger.error(f"处理文件选项缓存失败: {e}")
            raise


def refresh_all_cache_from_mysql():
    """从MySQL重新加载所有缓存"""
    logger.info("开始从MySQL刷新所有缓存...")

    # 清除现有缓存
    with tiku_cache_lock:
        TIKU_LIST_CACHE['data'] = None

    with file_options_cache_lock:
        FILE_OPTIONS_CACHE['data'] = None

    # 重新加载缓存
    try:
        tiku_data = get_cached_tiku_list()
        file_options_data = get_cached_file_options()

        result = {
            'tiku_count': len(tiku_data['tiku_list']) if tiku_data else 0,
            'subjects_count': len(file_options_data) if file_options_data else 0,
            'message': '缓存刷新成功'
        }

        logger.info(f"缓存刷新完成: {result}")
        return result

    except Exception as e:
        logger.error(f"缓存刷新失败: {e}")
        raise


def increment_tiku_usage(tiku_id: int):
    """增加题库使用次数（内存统计）"""
    with usage_stats_lock:
        tiku_usage_stats[tiku_id] = tiku_usage_stats.get(tiku_id, 0) + 1
        logger.debug(f"Incremented usage for tiku_id: {tiku_id} -> {tiku_usage_stats[tiku_id]}")


def inject_user_progress(subjects_data, current_tiku_id, current_progress):
    """向缓存的subjects_data中注入用户进度信息"""
    if not current_tiku_id or not current_progress:
        return subjects_data

    # 深拷贝避免修改缓存数据
    import copy
    result = copy.deepcopy(subjects_data)

    # 找到对应的题库并添加进度信息
    for subject_name, subject_data in result.items():
        for file_info in subject_data['files']:
            if file_info['tiku_id'] == current_tiku_id:
                file_info['progress'] = current_progress
                break

    return result


@practice_bp.route('/file_options', methods=['GET'])
@login_required
@handle_api_error
def api_file_options():
    """获取可用题库选项"""
    subjects_data = {}

    # 获取当前练习进度
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    current_progress = None
    if current_tiku_id:
        current_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
        current_index = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        initial_total = get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)

        if current_indices and initial_total > 0:
            current_progress = {
                'current_question': current_index + 1,
                'total_questions': len(current_indices),
                'initial_total': initial_total,
                'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
                'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1),
                'progress_percent': min(100, (current_index / len(current_indices)) * 100) if current_indices else 0
            }

    # 从缓存获取题库列表数据
    try:
        cached_data = get_cached_file_options()
        subjects_data = inject_user_progress(cached_data, current_tiku_id, current_progress)
    except Exception as e:
        logger.warning(f"从缓存获取题库列表失败: {e}")
        subjects_data = {}

    return create_response(True, data={'subjects': subjects_data})


@practice_bp.route('/start_practice', methods=['POST'])
@login_required
@handle_api_error
def api_start_practice():
    """开始练习"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    tiku_id = data.get('tikuid')
    shuffle_questions = data.get('shuffle_questions', True)
    force_restart = data.get('force_restart', False)

    if not tiku_id:
        raise BadRequest("缺少题库ID")

    try:
        tiku_id = int(tiku_id)
    except ValueError:
        raise BadRequest("无效的题库ID格式")

    #题库存在于内存中
    question_bank = APP_WIDE_QUESTION_DATA[tiku_id]

    # 检查是否有现有会话
    existing_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    existing_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    if not force_restart and existing_tiku_id == tiku_id and existing_indices:
        return create_response(True, '恢复现有练习会话', {'resumed': True})

    # 开始新会话 - 增加题库使用次数统计
    increment_tiku_usage(tiku_id)

    question_indices = list(range(len(question_bank)))
    if shuffle_questions:
        random.shuffle(question_indices)

    # 设置session
    set_session_value(SESSION_KEYS['CURRENT_TIKU_ID'], tiku_id)
    set_session_value(SESSION_KEYS['QUESTION_INDICES'], question_indices)
    set_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    set_session_value(SESSION_KEYS['WRONG_INDICES'], [])
    set_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
    set_session_value(SESSION_KEYS['INITIAL_TOTAL'], len(question_indices))
    set_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
    set_session_value(SESSION_KEYS['QUESTION_STATUSES'], [QUESTION_STATUS['UNANSWERED']] * len(question_indices))
    set_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})

    practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
    return create_response(True, f'开始{practice_mode}', {'resumed': False})


@practice_bp.route('/practice/question', methods=['GET'])
@handle_api_error
def api_practice_question():
    """获取当前练习题目"""
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not current_tiku_id or current_tiku_id not in APP_WIDE_QUESTION_DATA:
        raise BadRequest("没有选择题库或会话已过期")

    question_bank = APP_WIDE_QUESTION_DATA[current_tiku_id]
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])
    if not q_indices:
        raise NotFound("没有可用题目或会话已过期")

    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    flash_messages = []

    # 检查是否需要开始新轮次
    if current_idx >= len(q_indices):
        wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        if not wrong_indices:
            return create_response(True, '练习完成！', {'redirect_to_completed': True})

        # 开始新轮次
        new_round_indices = list(wrong_indices)
        random.shuffle(new_round_indices)
        set_session_value(SESSION_KEYS['QUESTION_INDICES'], new_round_indices)
        set_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        set_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        round_number = get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) + 1
        set_session_value(SESSION_KEYS['ROUND_NUMBER'], round_number)
        set_session_value(SESSION_KEYS['QUESTION_STATUSES'], [QUESTION_STATUS['UNANSWERED']] * len(new_round_indices))
        set_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})

        flash_messages.append({
            'category': 'info',
            'text': f"开始第{round_number}轮，共{len(new_round_indices)}道错题！"
        })

        current_idx = 0
        q_indices = new_round_indices

    question_index = q_indices[current_idx]
    question_obj = question_bank[question_index]

    question_data = {
        'id': question_obj['id'],  # 现在是db_xxx格式
        'type': question_obj['type'],
        'question': question_obj['question'],
        'options_for_practice': question_obj.get('options_for_practice'),
        'answer': question_obj['answer'],
        'is_multiple_choice': question_obj.get('is_multiple_choice', False),
        'analysis': question_obj.get('explanation', '暂无解析'),  # 解析信息
        'knowledge_points': question_obj.get('knowledge_points', [])  # 知识点
    }

    progress_data = {
        'current': current_idx + 1,
        'total': len(q_indices),
        'initial_total': get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0),
        'correct_count': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
        'round_number': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
    }

    return create_response(True, data={
        'question': question_data,
        'progress': progress_data,
        'flash_messages': flash_messages
    })


@practice_bp.route('/practice/submit', methods=['POST'])
@handle_api_error
def api_submit_answer():
    """提交答案"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    user_answer = data.get('answer', '').upper()
    question_id = data.get('question_id')
    peeked = data.get('peeked', False)
    is_review = data.get('is_review', False)

    if not question_id:
        raise BadRequest("缺少题目ID")

    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    if not current_tiku_id or current_tiku_id not in APP_WIDE_QUESTION_DATA:
        raise BadRequest("无效的会话或题库")

    question_bank = APP_WIDE_QUESTION_DATA[current_tiku_id]
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    if current_idx >= len(q_indices):
        raise BadRequest("没有更多题目")

    question_index = q_indices[current_idx]
    question_data = question_bank[question_index]

    # 验证question_id是否匹配当前题目
    if question_data['id'] != question_id:
        logger.warning(f"Question ID mismatch: expected {question_data['id']}, got {question_id}")
        # 不抛出错误，继续处理，以保持兼容性

    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()

    # 判断答案是否正确
    is_correct = False if peeked else validate_answer(user_answer, correct_answer, is_multiple_choice)

    # 格式化答案显示
    options = question_data.get('options_for_practice', {})
    user_answer_display = '未作答（直接查看答案）' if peeked else format_answer_display(user_answer, options,
                                                                                      is_multiple_choice)
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    if not is_review:
        update_practice_record(question_data, is_correct, peeked, current_idx, user_answer)

    return create_response(True, data={
        "is_correct": is_correct,
        "user_answer_display": user_answer_display,
        "correct_answer_display": correct_answer_display,
        "question_id": question_id,
        "current_index": current_idx
    })


def update_practice_record(question_data, is_correct: bool, peeked: bool, current_idx: int, user_answer: str):
    """更新练习记录"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    actual_question_index = q_indices[current_idx]

    # 更新题目状态
    question_statuses = get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    if current_idx < len(question_statuses):
        question_statuses[current_idx] = QUESTION_STATUS['CORRECT'] if (is_correct and not peeked) else QUESTION_STATUS[
            'WRONG']
        set_session_value(SESSION_KEYS['QUESTION_STATUSES'], question_statuses)

    # 保存答题历史
    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    answer_history[str(current_idx)] = {
        'user_answer': user_answer,
        'is_correct': is_correct,
        'peeked': peeked,
        'question_data': question_data
    }
    set_session_value(SESSION_KEYS['ANSWER_HISTORY'], answer_history)

    # 处理错题和正确题
    if not is_correct or peeked:
        wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        if actual_question_index not in wrong_indices:
            wrong_indices.append(actual_question_index)
            set_session_value(SESSION_KEYS['WRONG_INDICES'], wrong_indices)
    else:
        if get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) == 1:
            correct_count = get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0) + 1
            set_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], correct_count)

    # 移动到下一题
    set_session_value(SESSION_KEYS['CURRENT_INDEX'], current_idx + 1)


@practice_bp.route('/completed_summary', methods=['GET'])
@handle_api_error
def api_completed_summary():
    """获取练习完成总结"""
    initial_total = get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
    correct_first_try = get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
    score_percent = (correct_first_try / initial_total * 100) if initial_total > 0 else 0

    # 获取当前题库信息
    tiku_info = get_current_tiku_info()
    display_name = tiku_info['tiku_name'] if tiku_info else 'Unknown'

    summary_data = {
        'initial_total': initial_total,
        'correct_first_try': correct_first_try,
        'score_percent': score_percent,
        'completed_filename': display_name
    }

    # 保存当前session到数据库后清除练习数据
    save_session_to_db()
    clear_practice_session()

    return create_response(True, data={'summary': summary_data})


@practice_bp.route('/practice/jump', methods=['GET'])
@handle_api_error
def api_jump_to_question():
    """跳转到指定题目"""
    target_index = request.args.get('index')
    if not target_index:
        raise BadRequest("缺少目标索引")

    try:
        target_index = int(target_index)
    except ValueError:
        raise BadRequest("无效的索引格式")

    if target_index < 0:
        raise BadRequest("无效的题目索引")

    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    if not q_indices or target_index >= len(q_indices):
        raise BadRequest("题目索引超出范围")

    set_session_value(SESSION_KEYS['CURRENT_INDEX'], target_index)
    return create_response(True, "成功跳转到题目")


@practice_bp.route('/practice/statuses', methods=['GET'])
@handle_api_error
def api_get_question_statuses():
    """获取所有题目状态"""
    statuses = get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    return create_response(True, data={'statuses': statuses})


@practice_bp.route('/practice/next', methods=['POST'])
@handle_api_error
def api_next_question():
    """跳转到下一题"""
    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    set_session_value(SESSION_KEYS['CURRENT_INDEX'], current_idx + 1)
    return create_response(True, "成功跳转到下一题")


@practice_bp.route('/session/status', methods=['GET'])
@login_required
@handle_api_error
def api_session_status():
    """获取会话状态"""
    current_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])

    if not current_tiku_id:
        return create_response(True, '没有活跃的练习会话', {'has_session': False})

    # 获取题库显示名称
    tiku_info = get_current_tiku_info()
    display_name = tiku_info['tiku_name'] if tiku_info else str(current_tiku_id)

    current_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_index = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    return create_response(True, '当前有活跃的练习会话', {
        'has_session': True,
        'tiku_id': current_tiku_id,
        'file_info': {
            'display': display_name,
            'current_question': current_index + 1,
            'total_questions': len(current_indices)
        }
    })


@practice_bp.route('/session/save', methods=['GET'])
@login_required
@handle_api_error
def api_save_session():
    """保存当前会话到数据库"""
    save_session_to_db()
    return create_response(True, '会话保存成功')


@practice_bp.route('/practice/history/<int:question_index>', methods=['GET'])
@handle_api_error
def api_get_question_history(question_index: int):
    """获取题目答题历史"""
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])

    if question_index < 0 or question_index >= len(q_indices):
        raise BadRequest(f'无效的题目索引。有效范围: 0-{len(q_indices) - 1}')

    answer_history = get_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    history_key = str(question_index)

    if history_key not in answer_history:
        raise NotFound('该题目没有答题历史')

    history_data = answer_history[history_key]
    question_data = history_data['question_data']

    # 格式化答案显示
    options = question_data.get('options_for_practice', {})
    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()
    user_answer = history_data['user_answer']

    user_answer_display = '未作答（直接查看答案）' if history_data['peeked'] else format_answer_display(user_answer,
                                                                                                      options,
                                                                                                      is_multiple_choice)
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    return create_response(True, data={
        'question': {
            'id': question_data['id'],
            'type': question_data['type'],
            'question': question_data['question'],
            'options_for_practice': question_data.get('options_for_practice'),
            'answer': question_data['answer'],
            'is_multiple_choice': question_data.get('is_multiple_choice', False),
            'analysis': question_data.get('explanation', '暂无解析'),  # 从explanation字段读取
            'knowledge_points': question_data.get('knowledge_points', [])
        },
        'feedback': {
            'is_correct': history_data['is_correct'],
            'user_answer_display': user_answer_display,
            'correct_answer_display': correct_answer_display,
            'question_id': question_data['id'],
            'current_index': question_index,
            'peeked': history_data['peeked']
        }
    })


@practice_bp.route('/practice/question/<question_id>/details', methods=['GET'])
@handle_api_error
def api_get_question_details(question_id: str):
    """获取题目详细信息（包含解析）"""
    # 从题目ID中提取数据库ID
    if not question_id.startswith('db_'):
        raise BadRequest('无效的题目ID格式')

    try:
        db_id = int(question_id.replace('db_', ''))
    except ValueError:
        raise BadRequest('无效的题目ID')

    # 从数据库获取题目详细信息
    questions = get_questions_by_tiku()  # 获取所有题目
    question_data = None

    for question in questions:
        if question.get('db_id') == db_id:
            question_data = question
            break

    if not question_data:
        raise NotFound('题目不存在')

    # 格式化选项
    options = question_data.get('options_for_practice', {})
    is_multiple_choice = question_data.get('is_multiple_choice', False)
    correct_answer = question_data['answer'].upper()

    # 格式化正确答案显示
    correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

    return create_response(True, data={
        'question': {
            'id': question_data['id'],
            'db_id': question_data['db_id'],
            'type': question_data['type'],
            'question': question_data['question'],
            'options_for_practice': question_data.get('options_for_practice'),
            'answer': question_data['answer'],
            'is_multiple_choice': question_data.get('is_multiple_choice', False),
            'explanation': question_data.get('explanation', '暂无解析'),
            'difficulty': question_data.get('difficulty', 1),
            'subject_name': question_data.get('subject_name'),
            'tiku_name': question_data.get('tiku_name'),
            'correct_answer_display': correct_answer_display
        }
    })


@practice_bp.route('/practice/question/<question_id>/analysis', methods=['GET'])
@login_required
@handle_api_error
def api_get_question_analysis(question_id: str):
    """获取题目解析"""
    # 从题目ID中提取数据库ID
    if not question_id.startswith('db_'):
        raise BadRequest('无效的题目ID格式')

    try:
        db_id = int(question_id.replace('db_', ''))
    except ValueError:
        raise BadRequest('无效的题目ID')

    # 从数据库获取题目详细信息
    questions = get_questions_by_tiku()  # 获取所有题目
    question_data = None

    for question in questions:
        if question.get('db_id') == db_id:
            question_data = question
            break

    if not question_data:
        raise NotFound('题目不存在')

    return create_response(True, data={
        'analysis': question_data.get('explanation', '暂无解析'),
        'knowledge_points': question_data.get('knowledge_points', [])
    })


@practice_bp.route('/practice', methods=['GET'])
@login_required
@handle_api_error
def api_practice_url_params():
    """支持简化URL参数格式的练习路由：/practice?tikuid=123&order=random"""
    # 获取URL参数
    tiku_id = request.args.get('tikuid')
    order = request.args.get('order', 'random')

    if not tiku_id:
        raise BadRequest("缺少必要的URL参数: tikuid")

    try:
        tiku_id = int(tiku_id)
    except ValueError:
        raise BadRequest("无效的题库ID格式")

    logger.info(f"URL practice access: tikuid={tiku_id}, order={order}")

    # 从数据库获取题库信息
    try:
        from ..connectDB import get_tiku_by_subject
        tiku_list = get_tiku_by_subject()
        tiku_info = None

        for tiku in tiku_list:
            if tiku['tiku_id'] == tiku_id:
                tiku_info = tiku
                break

        if not tiku_info:
            raise NotFound(f"未找到题库ID: {tiku_id}")

        if not tiku_info['is_active']:
            raise BadRequest(f"题库已禁用: {tiku_info['tiku_name']}")

        tiku_position = tiku_info['tiku_position']

    except Exception as e:
        logger.warning(f"查找题库失败: {e}")
        raise NotFound(f"查找题库失败: {tiku_id}")

    # 检查题库是否存在于内存中，注意APP_WIDE_QUESTION_DATA可能使用tiku_id或tiku_position作为键
    question_bank = None
    if tiku_id in APP_WIDE_QUESTION_DATA:
        question_bank = APP_WIDE_QUESTION_DATA[tiku_id]
    elif tiku_position in APP_WIDE_QUESTION_DATA:
        question_bank = APP_WIDE_QUESTION_DATA[tiku_position]
    else:
        raise NotFound("选择的题库未加载到内存中")

    # 检查是否有现有会话
    existing_tiku_id = get_session_value(SESSION_KEYS['CURRENT_TIKU_ID'])
    existing_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    # 确定题目顺序
    shuffle_questions = order.lower() == 'random'

    if existing_tiku_id != tiku_id or not existing_indices:
        # 开始新的练习会话
        if not isinstance(question_bank, list) or not question_bank:
            raise BadRequest('选择的题库为空或无效')

        # 增加题库使用次数统计
        increment_tiku_usage(tiku_id)

        question_indices = list(range(len(question_bank)))
        if shuffle_questions:
            random.shuffle(question_indices)

        # 设置session
        set_session_value(SESSION_KEYS['CURRENT_TIKU_ID'], tiku_id)
        set_session_value(SESSION_KEYS['QUESTION_INDICES'], question_indices)
        set_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        set_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        set_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        set_session_value(SESSION_KEYS['INITIAL_TOTAL'], len(question_indices))
        set_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
        set_session_value(SESSION_KEYS['QUESTION_STATUSES'], [QUESTION_STATUS['UNANSWERED']] * len(question_indices))
        set_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})

        practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
        logger.info(f"开始新的{practice_mode}: {tiku_info['tiku_name']} (ID: {tiku_id})")

    # 获取当前题目数据
    try:
        question_response = api_practice_question()

        # 如果是重定向到完成页面
        if isinstance(question_response, tuple):
            response_data, status_code = question_response
            response_json = response_data.get_json()
            if response_json.get('redirect_to_completed'):
                return create_response(True, '练习完成！', {
                    'redirect_to_completed': True,
                    'url_mode': True
                })

        # 正常返回题目数据，添加URL模式标识
        if isinstance(question_response, tuple):
            response_data, status_code = question_response
            response_json = response_data.get_json()
            if response_json.get('success'):
                response_json['url_mode'] = True
                response_json['url_params'] = {
                    'tikuid': tiku_id,
                    'order': order,
                    'tiku_position': tiku_position,
                    'tiku_name': tiku_info['tiku_name'],
                    'subject_name': tiku_info['subject_name']
                }
                return jsonify(response_json), status_code

        return question_response

    except Exception as e:
        logger.error(f"获取题目失败: {e}")
        raise BadRequest(f"获取题目失败: {str(e)}")


# 缓存管理API - 只保留从MySQL刷新缓存的接口
@practice_bp.route('/cache/refresh', methods=['POST'])
@login_required
@handle_api_error
def api_refresh_cache_from_mysql():
    """从MySQL重新加载所有缓存"""
    try:
        result = refresh_all_cache_from_mysql()
        return create_response(True, result['message'], {
            'tiku_count': result['tiku_count'],
            'subjects_count': result['subjects_count']
        })
    except Exception as e:
        logger.error(f"刷新缓存失败: {e}")
        return create_response(False, f'刷新缓存失败: {str(e)}', status_code=500)
