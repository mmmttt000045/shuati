import glob  # For finding files
import logging  # 用于控制日志输出
import os
import random
import threading  # 用于后台线程
import time  # 用于定期任务
import traceback  # 用于更详细的错误打印
from datetime import timedelta
from typing import List, Dict, Optional, Union, Any
from functools import wraps

import pandas as pd
from flask import Flask, request, session, jsonify, send_from_directory, Response
from flask_cors import CORS  # 添加 CORS 支持
from werkzeug.exceptions import NotFound, BadRequest

# 导入数据库连接和用户认证相关函数
from connectDB import (
    authenticate_user,
    create_user,
    verify_invitation_code,
    get_user_info,
    get_user_model,
    create_invitation_code,
    save_user_session,
    load_user_session,
    delete_user_session,
    update_session_timestamp,
    cleanup_expired_sessions
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('quiz_app.log')
    ]
)
logger = logging.getLogger(__name__)

# --- 配置 ---
# EXCEL_FILELIST is now obsolete, will be discovered
SUBJECT_DIRECTORY = 'subject'  # New constant for the subjects directory
SHEET_NAME = 0

# --- 列名常量 ---
QUESTION_COLUMN = '题干'
OPTION_A_COLUMN = 'A'
OPTION_B_COLUMN = 'B'
OPTION_C_COLUMN = 'C'
OPTION_D_COLUMN = 'D'
ANSWER_COLUMN = '答案'
TYPE_COLUMN = '题型'

# --- 判断题答案标准化常量 ---
TRUE_ANSWER_STRINGS = ["T", "t", "Y", "y", "正确", "对", "√", "是"]
FALSE_ANSWER_STRINGS = ["F", "f", "N", "n", "错误", "错", "×", "否"]
INTERNAL_TRUE = "T"
INTERNAL_FALSE = "F"

# --- Excel 输出错题集列顺序 ---
COLUMNS_FOR_EXCEL_OUTPUT = [QUESTION_COLUMN, OPTION_A_COLUMN, OPTION_B_COLUMN, OPTION_C_COLUMN, OPTION_D_COLUMN,
                            ANSWER_COLUMN, TYPE_COLUMN]

# --- Session keys ---
SESSION_KEYS = {
    'CURRENT_EXCEL_FILE': 'current_excel_file',
    'QUESTION_INDICES': 'q_indices_to_practice',
    'QUESTION_ORDER': 'question_order',  # 添加题目顺序键
    'CURRENT_INDEX': 'current_idx_in_indices_list',
    'WRONG_INDICES': 'wrong_q_indices_this_round',
    'ROUND_NUMBER': 'round_number',
    'INITIAL_TOTAL': 'initial_total_questions',
    'CORRECT_FIRST_TRY': 'correct_on_first_try',
    'QUESTION_STATUSES': 'question_answer_statuses',  # 保存每道题的答题状态
    'ANSWER_HISTORY': 'question_answer_history',  # 保存每道题的答题历史
    'USER_ID': 'user_id',  # 用户ID
    'USERNAME': 'username'  # 用户名
}

# --- Session管理策略 ---
# --- 题目状态常量 ---
# 使用数字代替字符串，节省内存和传输带宽
QUESTION_STATUS = {
    'UNANSWERED': 0,  # 未作答
    'CORRECT': 1,  # 答对
    'WRONG': 2  # 答错/查看答案
}

# 状态映射（用于调试和日志）
QUESTION_STATUS_NAMES = {
    0: 'unanswered',
    1: 'correct',
    2: 'wrong'
}


# --- 公共工具函数 ---
def create_response(success: bool = True, message: str = '', data: Any = None, status_code: int = 200) -> tuple[
    Response, int]:
    """统一的API响应格式"""
    response_data = {'success': success}
    if message:
        response_data['message'] = message
    if data is not None:
        if isinstance(data, dict):
            response_data.update(data)
        else:
            response_data['data'] = data
    return jsonify(response_data), status_code


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
    """检查用户是否已登录的装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        username = session.get('username')

        if not user_id or not username:
            return create_response(False, '请先登录', status_code=401)

        return f(*args, **kwargs)

    return decorated_function


def standardize_tf_answer(answer_text: Optional[str]) -> Optional[str]:
    """标准化判断题答案"""
    if not isinstance(answer_text, str):
        return None
    answer_upper = answer_text.strip().upper()
    if answer_upper == INTERNAL_TRUE or any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS):
        return INTERNAL_TRUE
    if answer_upper == INTERNAL_FALSE or any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS):
        return INTERNAL_FALSE
    return None


def is_tf_answer(answer_text: str) -> bool:
    """检查是否为判断题答案"""
    if not isinstance(answer_text, str):
        return False
    answer_upper = answer_text.strip().upper()
    return (any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS) or
            any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS))


def normalize_filepath(filepath: str) -> str:
    """标准化文件路径"""
    return filepath.replace("\\", "/")


def get_session_value(key: str, default: Any = None) -> Any:
    """安全获取session值"""
    return session.get(key, default)


def set_session_value(key: str, value: Any) -> None:
    """安全设置session值"""
    session[key] = value
    session.modified = True


def clear_practice_session() -> None:
    """清除练习相关的session数据"""
    practice_keys = [
        SESSION_KEYS['CURRENT_EXCEL_FILE'], SESSION_KEYS['QUESTION_INDICES'],
        SESSION_KEYS['CURRENT_INDEX'], SESSION_KEYS['WRONG_INDICES'],
        SESSION_KEYS['ROUND_NUMBER'], SESSION_KEYS['INITIAL_TOTAL'],
        SESSION_KEYS['CORRECT_FIRST_TRY'], SESSION_KEYS['QUESTION_STATUSES'],
        SESSION_KEYS['ANSWER_HISTORY']
    ]

    for key in practice_keys:
        session.pop(key, None)
    session.modified = True


def save_session_to_db() -> None:
    """保存当前session到数据库"""
    user_id = session.get('user_id')
    if user_id:
        session_data = {key: session.get(key) for key in SESSION_KEYS.values() if key in session}
        if session_data:
            save_user_session(user_id, session_data)


def load_session_from_db() -> None:
    """从数据库加载session数据"""
    user_id = session.get('user_id')
    if user_id:
        user_session_data = load_user_session(user_id)
        if user_session_data:
            for key, value in user_session_data.items():
                session[key] = value
            session.modified = True


def format_answer_display(answer: str, options: dict, is_multiple_choice: bool) -> str:
    """格式化答案显示"""
    if not options:
        if answer.upper() == 'T':
            return 'T. 正确'
        elif answer.upper() == 'F':
            return 'F. 错误'
        return answer

    if is_multiple_choice:
        formatted_answers = []
        for letter in sorted(answer):
            if letter in options:
                formatted_answers.append(f"{letter}. {options[letter]}")
        return " + ".join(formatted_answers)
    else:
        return f"{answer}. {options.get(answer, '')}" if answer in options else answer


def validate_answer(user_answer: str, correct_answer: str, is_multiple_choice: bool) -> bool:
    """验证用户答案是否正确"""
    user_answer = user_answer.upper()
    correct_answer = correct_answer.upper()

    if is_multiple_choice:
        return set(user_answer) == set(correct_answer)
    else:
        return user_answer == correct_answer


def load_questions_from_excel(filepath: str, sheetname: Union[str, int]) -> Optional[List[Dict[str, Any]]]:
    """从Excel文件加载题目"""
    if not os.path.exists(filepath):
        logger.error(f"Question bank file '{filepath}' not found.")
        return None

    try:
        df = pd.read_excel(filepath, sheet_name=sheetname, dtype=str)
        df.columns = [col.strip() for col in df.columns]

        required_cols = [QUESTION_COLUMN, ANSWER_COLUMN]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns in '{filepath}': {', '.join(missing_cols)}")
            return []

        questions_data = []
        for index, row in df.iterrows():
            try:
                question_text = str(row.get(QUESTION_COLUMN, '')).strip()
                raw_answer_text = str(row.get(ANSWER_COLUMN, '')).strip()

                if not question_text or not raw_answer_text or question_text.lower() == 'nan' or raw_answer_text.lower() == 'nan':
                    continue

                # 处理判断题
                if is_tf_answer(raw_answer_text):
                    processed_answer = standardize_tf_answer(raw_answer_text)
                    if not processed_answer:
                        continue
                    question_type = '判断题'
                    options_for_practice = None
                else:
                    # 处理选择题
                    options_for_practice = {}
                    for option_key in ['A', 'B', 'C', 'D']:
                        option_text = str(row.get(option_key, '')).strip()
                        if option_text and option_text.lower() != 'nan':
                            options_for_practice[option_key] = option_text

                    if not options_for_practice:
                        processed_answer = standardize_tf_answer(raw_answer_text)
                        if processed_answer:
                            question_type = '判断题'
                            options_for_practice = None
                        else:
                            continue
                    else:
                        processed_answer = raw_answer_text.strip().upper()
                        if processed_answer.endswith(".0"):
                            processed_answer = processed_answer[:-2]

                        # 验证答案
                        if not all(char in options_for_practice for char in processed_answer):
                            continue

                        question_type = '多选题' if len(processed_answer) > 1 else '单选题'

                questions_data.append({
                    'id': f"{filepath}_{index}",
                    'type': question_type,
                    'question': question_text,
                    'options_for_practice': options_for_practice,
                    'answer': processed_answer,
                    'is_multiple_choice': question_type == '多选题'
                })
            except Exception as e:
                logger.warning(f"Error processing question at index {index} in '{filepath}': {e}")
                continue

        logger.info(f"Loaded {len(questions_data)} questions from '{filepath}'")
        return questions_data

    except Exception as e:
        logger.error(f"Critical error loading questions from '{filepath}': {e}")
        return None


# --- Flask App Initialization ---
app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
app.secret_key = 'your-fixed-secret-key-here'  # 使用固定的 secret key 方便调试

# 配置 session
app.config.update(
    SESSION_COOKIE_SECURE=False,  # Development setting
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',  # Allow cross-site cookies in development
    SESSION_COOKIE_NAME='quiz_session',
    SESSION_COOKIE_DOMAIN=None,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),  # 增加session过期时间到2小时
    SESSION_COOKIE_MAX_AGE=7200,  # 2小时的秒数
    SESSION_REFRESH_EACH_REQUEST=True  # 每次请求都刷新session过期时间
)

# 配置 CORS - 更宽松的开发环境配置
cors = CORS(app,
            resources={
                r"/*": {  # 允许所有路径
                    "origins": ["*"],
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # 允许的方法
                    "allow_headers": ["Content-Type", "Authorization", "Accept", "Origin",
                                      "X-Requested-With", "Cache-Control", "Pragma"],  # 允许的头部
                    "supports_credentials": True
                }
            })

# --- 预加载所有题库 ---
APP_WIDE_QUESTION_DATA = {}


def get_all_excel_files():
    """获取所有Excel文件"""
    pattern = os.path.join(SUBJECT_DIRECTORY, "*", "*.xlsx")
    files = glob.glob(pattern)

    # 也查找直接在subject目录下的文件
    pattern_direct = os.path.join(SUBJECT_DIRECTORY, "*.xlsx")
    files.extend([f for f in glob.glob(pattern_direct) if f not in files])

    return [f.replace("\\", "/") for f in files]


def load_all_banks():
    """加载所有题库"""
    data = {}
    logger.info(f"Scanning '{SUBJECT_DIRECTORY}' directory for question banks")

    if not os.path.exists(SUBJECT_DIRECTORY):
        os.makedirs(SUBJECT_DIRECTORY)
        logger.info(f"Created '{SUBJECT_DIRECTORY}' directory")
        return data

    excel_files = get_all_excel_files()
    if not excel_files:
        logger.warning(f"No .xlsx files found in '{SUBJECT_DIRECTORY}' directory")

    for filepath in excel_files:
        questions = load_questions_from_excel(filepath, SHEET_NAME)
        data[filepath] = questions if questions is not None else []

    logger.info(f"Loaded {len(data)} question banks")
    return data


APP_WIDE_QUESTION_DATA = load_all_banks()

# --- 新增：用于定期打印连接信息的全局变量和锁 ---
request_counter = 0
request_counter_lock = threading.Lock()
stop_event = threading.Event()  # 用于通知后台线程停止


def monitor_activity():
    """后台活动监控"""
    global request_counter
    cleanup_counter = 0

    while not stop_event.is_set():
        time.sleep(30)
        if stop_event.is_set():
            break

        with request_counter_lock:
            current_count = request_counter
            request_counter = 0

        logger.info(f"Server active. Requests in last 30s: {current_count}")

        cleanup_counter += 1
        if cleanup_counter >= 10:  # 每5分钟清理一次
            try:
                cleaned = cleanup_expired_sessions()
                if cleaned > 0:
                    logger.info(f"Cleaned {cleaned} expired sessions")
            except Exception as e:
                logger.error(f"Error cleaning sessions: {e}")
            cleanup_counter = 0


@app.before_request
def before_request():
    """请求前处理"""
    global request_counter
    with request_counter_lock:
        request_counter += 1
    session.permanent = True


@app.after_request
def after_request(response):
    """请求后处理"""
    session.modified = True
    return response


# --- Flask Routes ---
@app.route('/')
@app.route('/<path:path>')
def serve_app(path: str = '') -> Response:
    """服务前端应用"""
    try:
        dist_path = os.path.join(app.static_folder, '../frontend/dist')
        if path and os.path.exists(os.path.join(dist_path, path)):
            return send_from_directory('../frontend/dist', path)
        return send_from_directory('../frontend/dist', 'index.html')
    except Exception:
        return create_response(False, 'Failed to serve application', status_code=500)[0]


# --- 用户认证相关路由 ---
@app.route('/api/auth/register', methods=['POST'])
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


@app.route('/api/auth/login', methods=['POST'])
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


@app.route('/api/auth/logout', methods=['POST'])
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


@app.route('/api/auth/user', methods=['GET'])
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


@app.route('/api/auth/check', methods=['GET'])
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


@app.route('/api/file_options', methods=['GET'])
@login_required
@handle_api_error
def api_file_options():
    """获取可用题库选项"""
    subjects_data = {}

    if not APP_WIDE_QUESTION_DATA:
        return create_response(True, 'No question banks available', {'subjects': {}})

    # 获取当前练习进度
    current_file = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    current_progress = None
    if current_file:
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

    for filepath, questions_list in APP_WIDE_QUESTION_DATA.items():
        path_parts = normalize_filepath(filepath).split('/')
        if len(path_parts) < 2:
            continue

        filename = path_parts[-1].replace('.xlsx', '').replace('.xls', '')
        subject = path_parts[1] if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY else "未分类"

        if subject not in subjects_data:
            subjects_data[subject] = []

        file_info = {
            'key': filepath,
            'display': filename,
            'count': len(questions_list) if isinstance(questions_list, list) else 0,
            'progress': current_progress if current_file == filepath else None
        }
        subjects_data[subject].append(file_info)

    # 排序
    sorted_subjects = {
        subject: sorted(files, key=lambda x: x['display'])
        for subject, files in sorted(subjects_data.items())
    }

    return create_response(True, data={'subjects': sorted_subjects})


@app.route('/api/start_practice', methods=['POST'])
@login_required
@handle_api_error
def api_start_practice():
    """开始练习"""
    data = request.get_json()
    if not data:
        raise BadRequest("缺少请求数据")

    subject_name = data.get('subject')
    file_name = data.get('fileName')
    force_restart = data.get('force_restart', False)
    shuffle_questions = data.get('shuffle_questions', True)

    if not subject_name or not file_name:
        raise BadRequest("缺少科目名称或文件名")

    if file_name not in APP_WIDE_QUESTION_DATA:
        raise NotFound("选择的题库未找到")

    question_bank = APP_WIDE_QUESTION_DATA[file_name]
    if not isinstance(question_bank, list) or not question_bank:
        raise BadRequest('选择的题库为空或无效')

    # 检查是否有现有会话
    existing_file = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    existing_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    if not force_restart and existing_file == file_name and existing_indices:
        return create_response(True, '恢复现有练习会话', {'resumed': True})

    # 开始新会话
    question_indices = list(range(len(question_bank)))
    if shuffle_questions:
        random.shuffle(question_indices)

    # 设置session
    set_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'], file_name)
    set_session_value(SESSION_KEYS['QUESTION_INDICES'], question_indices)
    set_session_value(SESSION_KEYS['QUESTION_ORDER'], question_indices)
    set_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    set_session_value(SESSION_KEYS['WRONG_INDICES'], [])
    set_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
    set_session_value(SESSION_KEYS['INITIAL_TOTAL'], len(question_indices))
    set_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
    set_session_value(SESSION_KEYS['QUESTION_STATUSES'], [QUESTION_STATUS['UNANSWERED']] * len(question_indices))
    set_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})

    practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
    return create_response(True, f'开始{practice_mode}', {'resumed': False})


@app.route('/api/practice/question', methods=['GET'])
@handle_api_error
def api_practice_question():
    """获取当前练习题目"""
    selected_file = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    if not selected_file or selected_file not in APP_WIDE_QUESTION_DATA:
        raise BadRequest("没有选择题库或会话已过期")

    question_bank = APP_WIDE_QUESTION_DATA[selected_file]
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

    return create_response(True, data={
        'question': {
            'id': question_obj['id'],
            'type': question_obj['type'],
            'question': question_obj['question'],
            'options_for_practice': question_obj.get('options_for_practice'),
            'answer': question_obj['answer'],
            'is_multiple_choice': question_obj.get('is_multiple_choice', False)
        },
        'progress': {
            'current': current_idx + 1,
            'total': len(q_indices),
            'round': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        },
        'flash_messages': flash_messages
    })


@app.route('/api/practice/submit', methods=['POST'])
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

    selected_file = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    if not selected_file or selected_file not in APP_WIDE_QUESTION_DATA:
        raise BadRequest("无效的会话或题库")

    question_bank = APP_WIDE_QUESTION_DATA[selected_file]
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    if current_idx >= len(q_indices):
        raise BadRequest("没有更多题目")

    question_index = q_indices[current_idx]
    question_data = question_bank[question_index]

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


@app.route('/api/completed_summary', methods=['GET'])
@handle_api_error
def api_completed_summary():
    """获取练习完成总结"""
    initial_total = get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
    correct_first_try = get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
    score_percent = (correct_first_try / initial_total * 100) if initial_total > 0 else 0

    completed_filename = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'], 'Unknown')
    display_name = completed_filename.replace('.xlsx', '').replace('.xls', '')

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


@app.route('/api/practice/jump', methods=['GET'])
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


@app.route('/api/session/status', methods=['GET'])
@handle_api_error
def api_session_status():
    """检查当前会话状态"""
    selected_file = get_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    q_indices = get_session_value(SESSION_KEYS['QUESTION_INDICES'])

    if not selected_file or not q_indices or selected_file not in APP_WIDE_QUESTION_DATA:
        return create_response(True, '没有活跃的练习会话', {'active': False})

    current_idx = get_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
    wrong_indices = get_session_value(SESSION_KEYS['WRONG_INDICES'], [])

    if current_idx >= len(q_indices) and not wrong_indices:
        return create_response(True, '练习会话已完成', {'active': True, 'completed': True})

    # 提取文件信息
    path_parts = normalize_filepath(selected_file).split('/')
    display_name = path_parts[-1].replace('.xlsx', '').replace('.xls', '')
    subject = path_parts[1] if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY else "未分类"

    # 获取题目顺序信息
    question_order = get_session_value(SESSION_KEYS['QUESTION_ORDER'], [])
    initial_order = list(range(len(APP_WIDE_QUESTION_DATA.get(selected_file, []))))
    is_shuffled = question_order != initial_order if question_order else False

    return create_response(True, data={
        'active': True,
        'completed': False,
        'file_info': {
            'key': selected_file,
            'display': display_name,
            'subject': subject,
            'order_mode': '乱序练习' if is_shuffled else '顺序练习'  # 添加顺序模式信息
        },
        'progress': {
            'current': current_idx + 1,
            'total': len(q_indices),
            'round': get_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        },
        'statistics': {
            'initial_total': get_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0),
            'correct_first_try': get_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0),
            'wrong_count': len(wrong_indices)
        },
        'question_statuses': get_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    })


@app.route('/api/session/save', methods=['GET'])
@login_required
@handle_api_error
def api_save_session():
    """保存当前会话到数据库"""
    save_session_to_db()
    return create_response(True, '会话保存成功')


@app.route('/api/practice/history/<int:question_index>', methods=['GET'])
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
            'analysis': question_data.get('analysis', '暂无解析'),
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


# --- 管理员功能相关路由 ---
def admin_required(f):
    """检查用户是否为管理员的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return create_response(False, '请先登录', status_code=401)
        
        user_model = get_user_model(user_id)
        if user_model != 10:  # ROOT用户
            return create_response(False, '权限不足，需要管理员权限', status_code=403)
        
        return f(*args, **kwargs)
    return decorated_function


@app.route('/api/admin/stats', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_stats():
    """获取系统统计信息"""
    try:
        from connectDB import get_db_connection
        
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
        
        cursor.execute("SELECT COUNT(*) FROM invitation_codes WHERE is_used = FALSE AND (expires_at IS NULL OR expires_at > NOW())")
        unused_invitations = cursor.fetchone()[0]
        
        # 题库统计
        total_questions = sum(len(questions) for questions in APP_WIDE_QUESTION_DATA.values() if questions)
        total_files = len(APP_WIDE_QUESTION_DATA)
        
        stats = {
            'users': {
                'total': total_users,
                'active': active_users,
                'admins': admin_users,
                'vips': vip_users
            },
            'invitations': {
                'total': total_invitations,
                'unused': unused_invitations
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


@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_users():
    """获取用户列表"""
    try:
        from connectDB import get_db_connection
        
        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")
        
        cursor = connection.cursor()
        
        query = """
        SELECT 
            u.id, u.username, u.is_enabled, u.created_at, u.last_time_login, u.model,
            i.code as invitation_code
        FROM user_accounts u
        LEFT JOIN invitation_codes i ON u.used_invitation_code_id = i.id
        ORDER BY u.created_at DESC
        """
        cursor.execute(query)
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
        
        return create_response(True, data={'users': users})
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@app.route('/api/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
@handle_api_error
def api_admin_toggle_user(user_id):
    """启用/禁用用户"""
    try:
        from connectDB import get_db_connection
        
        # 不能操作自己
        current_user_id = session.get('user_id')
        if user_id == current_user_id:
            raise BadRequest("不能操作自己的账户")
        
        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")
        
        cursor = connection.cursor()
        
        # 获取当前状态
        cursor.execute("SELECT is_enabled FROM user_accounts WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            raise NotFound("用户不存在")
        
        current_status = result[0]
        new_status = not current_status
        
        # 更新状态
        cursor.execute("UPDATE user_accounts SET is_enabled = %s WHERE id = %s", (new_status, user_id))
        connection.commit()
        
        action = "启用" if new_status else "禁用"
        return create_response(True, f"用户已{action}", data={'is_enabled': new_status})
        
    except Exception as e:
        logger.error(f"Error toggling user {user_id}: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@app.route('/api/admin/users/<int:user_id>/model', methods=['PUT'])
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
        
        from connectDB import get_db_connection
        
        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")
        
        cursor = connection.cursor()
        
        # 检查用户是否存在
        cursor.execute("SELECT id FROM user_accounts WHERE id = %s", (user_id,))
        if not cursor.fetchone():
            raise NotFound("用户不存在")
        
        # 更新模型
        cursor.execute("UPDATE user_accounts SET model = %s WHERE id = %s", (model, user_id))
        connection.commit()
        
        model_names = {0: "普通用户", 5: "VIP用户", 10: "管理员"}
        return create_response(True, f"用户权限已更新为{model_names[model]}", data={'model': model})
        
    except Exception as e:
        logger.error(f"Error updating user model {user_id}: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()


@app.route('/api/admin/invitations', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_invitations():
    """获取邀请码列表"""
    try:
        from connectDB import get_db_connection
        
        connection = get_db_connection()
        if not connection:
            raise Exception("数据库连接失败")
        
        cursor = connection.cursor()
        
        query = """
        SELECT 
            i.id, i.code, i.is_used, i.created_at, i.expires_at,
            u.username as used_by_username
        FROM invitation_codes i
        LEFT JOIN user_accounts u ON i.used_by_user_id = u.id
        ORDER BY i.created_at DESC
        """
        cursor.execute(query)
        invitations_data = cursor.fetchall()
        
        invitations = []
        for invitation_data in invitations_data:
            inv_id, code, is_used, created_at, expires_at, used_by_username = invitation_data
            invitations.append({
                'id': inv_id,
                'code': code,
                'is_used': bool(is_used),
                'created_at': created_at.isoformat() if created_at else None,
                'expires_at': expires_at.isoformat() if expires_at else None,
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


@app.route('/api/admin/invitations', methods=['POST'])
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
        
        result = create_invitation_code(code, expire_days)
        if result['success']:
            return create_response(True, result['message'], data={'invitation_code': result['code']})
        else:
            raise BadRequest(result['error'])
        
    except Exception as e:
        logger.error(f"Error creating invitation: {e}")
        raise


@app.route('/api/admin/subject-files', methods=['GET'])
@login_required
@admin_required
@handle_api_error
def api_admin_get_subject_files():
    """获取题库文件信息"""
    try:
        files_info = []
        
        for filepath, questions in APP_WIDE_QUESTION_DATA.items():
            try:
                # 解析文件路径
                path_parts = normalize_filepath(filepath).split('/')
                filename = path_parts[-1]
                display_name = filename.replace('.xlsx', '').replace('.xls', '')
                subject = path_parts[1] if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY else "未分类"
                
                # 获取文件信息
                file_size = 0
                modified_time = None
                if os.path.exists(filepath):
                    stat = os.stat(filepath)
                    file_size = stat.st_size
                    modified_time = datetime.fromtimestamp(stat.st_mtime)
                
                files_info.append({
                    'subject': subject,
                    'filename': filename,
                    'display_name': display_name,
                    'file_path': filepath,
                    'question_count': len(questions) if isinstance(questions, list) else 0,
                    'file_size': file_size,
                    'modified_time': modified_time.isoformat() if modified_time else None
                })
            except Exception as e:
                logger.warning(f"Error processing file {filepath}: {e}")
                continue
        
        # 按科目和文件名排序
        files_info.sort(key=lambda x: (x['subject'], x['filename']))
        
        return create_response(True, data={'files': files_info})
        
    except Exception as e:
        logger.error(f"Error getting subject files: {e}")
        raise


# --- 辅助函数 ---
def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


if __name__ == '__main__':
    import sys

    # 创建目录
    if not os.path.exists(SUBJECT_DIRECTORY):
        os.makedirs(SUBJECT_DIRECTORY)

    # 配置日志 - 确保日志可以在后台运行时正常工作
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # 如果检测到nohup环境，重定向标准输入输出
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        # 在nohup环境中，重定向标准输入到/dev/null（Windows上使用NUL）
        try:
            if os.name == 'nt':  # Windows
                sys.stdin = open('NUL', 'r')
            else:  # Unix/Linux
                sys.stdin = open('/dev/null', 'r')
        except Exception as e:
            logger.warning(f"Failed to redirect stdin: {e}")

    # 启动后台监控线程
    activity_thread = threading.Thread(target=monitor_activity, daemon=True)
    activity_thread.start()

    HOST = '127.0.0.1'
    PORT = 5051

    logger.info(f"Starting Flask application on http://{HOST}:{PORT}")

    try:
        # 尝试使用高性能服务器
        try:
            import gunicorn.app.base


            class StandaloneApplication(gunicorn.app.base.BaseApplication):
                def __init__(self, app, options=None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    config = {key: value for key, value in self.options.items()
                              if key in self.cfg.settings and value is not None}
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application


            options = {
                'bind': f'{HOST}:{PORT}',
                'workers': 9,
                'worker_class': 'sync',
                'timeout': 30,
                'keepalive': 2,
                'max_requests': 1000,
                'preload_app': True,
                'loglevel': 'info',
                'daemon': False,
                'pidfile': None,
                'access_log_format': '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
            }

            logger.info("Using Gunicorn server")
            StandaloneApplication(app, options).run()

        except ImportError:
            try:
                from waitress import serve

                logger.info("Using Waitress server")
                # Waitress配置，更适合后台运行
                serve(app,
                      host=HOST,
                      port=PORT,
                      threads=6,
                      connection_limit=100,
                      cleanup_interval=30,
                      channel_timeout=120)
            except ImportError:
                logger.warning("Using Flask dev server (not recommended for production)")
                # 对于开发服务器，禁用重载器以避免nohup问题
                app.run(host=HOST, port=PORT, debug=False, use_reloader=False, threaded=True)

    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        sys.exit(1)
    finally:
        stop_event.set()
        if activity_thread.is_alive():
            activity_thread.join(timeout=5)
        logger.info("Server shutdown complete")
