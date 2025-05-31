import glob  # For finding files
import logging  # 用于控制日志输出
import os
import random
import threading  # 用于后台线程
import time  # 用于定期任务
import traceback  # 用于更详细的错误打印
from datetime import timedelta
from typing import List, Dict, Optional, Union, Any

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
    'CORRECT': 1,     # 答对
    'WRONG': 2        # 答错/查看答案
}

# 状态映射（用于调试和日志）
QUESTION_STATUS_NAMES = {
    0: 'unanswered',
    1: 'correct', 
    2: 'wrong'
}

# --- 用户认证装饰器 ---
def login_required(f):
    """检查用户是否已登录的装饰器"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        username = session.get('username')
        
        # 详细的session检查和日志
        if not user_id:
            logger.warning(f"Access denied to {request.endpoint}: No user_id in session. Session keys: {list(session.keys())}")
            return jsonify({'success': False, 'error': '请先登录'}), 401
            
        if not username:
            logger.warning(f"Access denied to {request.endpoint}: user_id={user_id} but no username in session")
            return jsonify({'success': False, 'error': '会话信息不完整，请重新登录'}), 401
            
        # 记录成功的认证访问
        logger.debug(f"Authenticated access to {request.endpoint} by user {username} (id: {user_id})")
        
        return f(*args, **kwargs)
    return decorated_function

# --- 辅助函数 ---
def standardize_tf_answer(answer_text: Optional[str]) -> Optional[str]:
    """Standardize true/false answers to internal format."""
    if not isinstance(answer_text, str):
        return None
    answer_upper = answer_text.strip().upper()
    if answer_upper == INTERNAL_TRUE or any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS):
        return INTERNAL_TRUE
    if answer_upper == INTERNAL_FALSE or any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS):
        return INTERNAL_FALSE
    return None


def is_tf_answer(answer_text: str) -> bool:
    """Check if an answer is a true/false answer."""
    if not isinstance(answer_text, str):
        return False
    answer_upper = answer_text.strip().upper()
    return (any(true_str.upper() == answer_upper for true_str in TRUE_ANSWER_STRINGS) or
            any(false_str.upper() == answer_upper for false_str in FALSE_ANSWER_STRINGS))


def normalize_filepath(filepath: str) -> str:
    """Normalize file path separators."""
    return filepath.replace("\\", "/")


def get_safe_session_value(key: str, default: Any = None) -> Any:
    """Safely get a value from the session."""
    try:
        # 直接从本地session获取，不再每次都从数据库加载
        value = session.get(key, default)
        return value
    except Exception as e:
        logger.error(f"Error accessing session key '{key}': {e}")
        return default


def set_safe_session_value(key: str, value: Any) -> None:
    """Safely set a value in the session."""
    try:
        # 只保存到本地session，不再每次都保存到数据库
        session[key] = value
        session.modified = True
    except Exception as e:
        logger.error(f"Error setting session key '{key}': {e}")


def clear_user_session() -> None:
    """清除用户session数据"""
    try:
        user_id = session.get('user_id')
        if user_id:
            # 在清除前，将当前session数据保存到数据库（登出时保存）
            session_data = {}
            for key in SESSION_KEYS.values():
                if key in session:
                    session_data[key] = session[key]
            
            if session_data:
                save_user_session(user_id, session_data)
                logger.info(f"Session data saved to database for user {user_id} on logout")
        
        # 清除本地session
        session.clear()
        session.modified = True
    except Exception as e:
        logger.error(f"Error clearing user session: {e}")


def refresh_user_session() -> None:
    """刷新用户session时间戳 - 现在只在登录时使用"""
    try:
        user_id = session.get('user_id')
        if user_id:
            update_session_timestamp(user_id)
    except Exception as e:
        logger.error(f"Error refreshing user session: {e}")


def load_session_from_db() -> None:
    """从数据库加载session数据到本地session - 只在登录时使用"""
    try:
        user_id = session.get('user_id')
        if user_id:
            user_session_data = load_user_session(user_id)
            if user_session_data:
                # 将数据库中的session数据同步到本地session
                for key, value in user_session_data.items():
                    session[key] = value
                session.modified = True
                logger.info(f"Session data loaded from database for user {user_id}")
    except Exception as e:
        logger.error(f"Error loading session from database: {e}")


def load_questions_from_excel(filepath: str, sheetname: Union[str, int]) -> Optional[List[Dict[str, Any]]]:
    """
    Load questions from an Excel file.
    
    Args:
        filepath: Path to the Excel file
        sheetname: Name or index of the sheet to load
        
    Returns:
        List of question dictionaries or None if critical error occurs
    """
    questions_data = []
    try:
        if not os.path.exists(filepath):
            logger.error(f"Question bank file '{filepath}' not found.")
            return None

        df = pd.read_excel(filepath, sheet_name=sheetname, dtype=str)
        actual_columns = [col.strip() for col in df.columns]
        df.columns = actual_columns

        required_base_cols = [QUESTION_COLUMN, ANSWER_COLUMN]
        missing_base_cols = [col for col in required_base_cols if col not in df.columns]
        if missing_base_cols:
            logger.error(
                f"Missing required columns in '{filepath}' (sheet: '{sheetname}'): {', '.join(missing_base_cols)}")
            return []

        for index, row in df.iterrows():
            try:
                question_text = str(row.get(QUESTION_COLUMN, '')).strip()
                raw_answer_text = str(row.get(ANSWER_COLUMN, '')).strip()

                if not question_text or not raw_answer_text or question_text.lower() == 'nan' or raw_answer_text.lower() == 'nan':
                    continue

                # Check if it's a true/false question
                if is_tf_answer(raw_answer_text):
                    processed_answer = standardize_tf_answer(raw_answer_text)
                    if not processed_answer:
                        logger.warning(
                            f"Skipping true/false question with invalid answer format: '{filepath}' -> '{question_text[:30]}...' answer: '{raw_answer_text}'")
                        continue
                    question_type = '判断题'
                    options_for_practice = None
                else:
                    # Check if it's a multiple choice question
                    has_valid_options = False
                    options_for_practice = {}

                    # Collect all valid options
                    for option_key in ['A', 'B', 'C', 'D']:
                        option_col = option_key
                        if option_col in df.columns:
                            option_text = str(row.get(option_col, '')).strip()
                            if option_text and option_text.lower() != 'nan':
                                has_valid_options = True
                                options_for_practice[option_key] = option_text

                    if not has_valid_options:
                        # Try to process as true/false question if no valid options
                        processed_answer = standardize_tf_answer(raw_answer_text)
                        if processed_answer:
                            question_type = '判断题'
                            options_for_practice = None
                        else:
                            logger.warning(
                                f"Skipping question with unrecognized type: '{filepath}' -> '{question_text[:30]}...'")
                            continue
                    else:
                        # Process as multiple choice question
                        question_type = '单选题'
                        processed_answer = raw_answer_text.strip().upper()
                        if processed_answer.endswith(".0"):
                            processed_answer = processed_answer[:-2]

                        # Validate answer
                        is_valid_answer = True
                        answer_size = 0
                        for answer_char in processed_answer:
                            answer_size += 1
                            if answer_char not in options_for_practice:
                                logger.warning(
                                    f"Answer '{answer_char}' not in valid options {list(options_for_practice.keys())}: '{filepath}' -> '{question_text[:30]}...'")
                                is_valid_answer = False
                                break

                        if answer_size > 1:
                            question_type = '多选题'
                        if not is_valid_answer:
                            continue

                # Add question to list
                questions_data.append({
                    'id': f"{filepath}_{index}",
                    'type': question_type,
                    'question': question_text,
                    'options_for_practice': options_for_practice,
                    'answer': processed_answer,
                    'is_multiple_choice': question_type == '多选题'
                })
            except Exception as e:
                logger.error(f"Error processing question at index {index} in '{filepath}': {e}")
                continue

        if not questions_data:
            logger.warning(f"No valid questions loaded from '{filepath}' (sheet: '{sheetname}')")

        return questions_data
    except Exception as e:
        logger.error(f"Critical error loading questions from '{filepath}': {e}")
        traceback.print_exc()
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


# --- Request Hooks ---
@app.before_request
def make_session_permanent():
    session.permanent = True


@app.after_request
def session_management(response):
    """Ensure session is saved."""
    try:
        # Force the session to be saved
        session.modified = True

    except Exception as e:
        logger.error(f"Error in session management: {e}")
    return response

# --- 预加载所有题库 ---
APP_WIDE_QUESTION_DATA = {}


def get_all_excel_files_from_subjects(base_dir):
    """Scans the base_dir for subject folders and excel files within them."""
    discovered_files = []
    # base_dir is 'subject'. We look for subject_folder/excel_file.xlsx
    # glob pattern: subject/*/*.xlsx
    pattern = os.path.join(base_dir, "*", "*.xlsx")
    for filepath in glob.glob(pattern):
        # Normalize path separators for consistency, especially on Windows
        discovered_files.append(filepath.replace("\\\\", "/"))

    # Also find files directly under base_dir if any (e.g. subject/SomeFile.xlsx - less common use case but to be safe)
    pattern_direct = os.path.join(base_dir, "*.xlsx")
    for filepath in glob.glob(pattern_direct):
        normalized_filepath = filepath.replace("\\\\", "/")
        if normalized_filepath not in discovered_files:  # Avoid duplicates if somehow matched by both
            discovered_files.append(normalized_filepath)
    return discovered_files


def load_all_banks():
    data = {}
    print(f"--- 开始扫描 '{SUBJECT_DIRECTORY}' 文件夹下的所有题库 ---")

    # Create subject directory if it doesn't exist
    if not os.path.exists(SUBJECT_DIRECTORY):
        os.makedirs(SUBJECT_DIRECTORY)
        print(
            f"已创建 '{SUBJECT_DIRECTORY}' 目录。请将您的题库Excel文件放入相应的科目子文件夹中 (例如 '{SUBJECT_DIRECTORY}/Java基础/题目.xlsx').")
        # No files to load yet if we just created it
        print(f"--- '{SUBJECT_DIRECTORY}' 文件夹扫描完毕 ---")
        return data

    excel_filepaths = get_all_excel_files_from_subjects(SUBJECT_DIRECTORY)

    if not excel_filepaths:
        print(f"警告: 在 '{SUBJECT_DIRECTORY}' 目录及其子目录中未找到任何 .xlsx 文件。")
        print(f"请确保您的题库Excel文件位于类似 '{SUBJECT_DIRECTORY}/<科目名称>/<题库文件名>.xlsx' 的路径下。")

    for filepath in excel_filepaths:
        questions = load_questions_from_excel(filepath, SHEET_NAME)
        if questions is not None:  # load_questions_from_excel returns None on critical error/file not found
            data[filepath] = questions  # Key is now the full relative path
            if questions:  # Empty list means file was parsable but had no valid questions
                print(f"成功从 '{filepath}' 加载 {len(questions)} 道题目。")
            else:
                print(f"信息: 从 '{filepath}' 未加载到题目 (文件可能为空或格式不符，但文件存在且可解析)。")
        else:
            # This case (questions is None) means file not found or critical load error
            data[filepath] = []  # Store as empty list to indicate attempted load but failed
            print(f"警告: 从 '{filepath}' 加载题目失败 (文件不存在或发生严重解析错误)。")
    print(f"--- '{SUBJECT_DIRECTORY}' 文件夹扫描完毕 ---")
    return data


APP_WIDE_QUESTION_DATA = load_all_banks()

# --- 新增：用于定期打印连接信息的全局变量和锁 ---
num_requests_since_last_check = 0
# 对于简单的开发服务器，且只有一个worker，锁可能不是严格必须的，但好习惯是加上
# 如果未来使用多进程/多线程的WSGI服务器（如gunicorn, uwsgi），这个简单的全局变量方式需要更复杂的处理（如IPC或外部存储）
# 这里我们假设是Flask开发服务器或者单进程的简单部署
request_counter_lock = threading.Lock()
stop_event = threading.Event()  # 用于通知后台线程停止


def print_activity_periodically():
    """后台线程函数，定期打印服务器活动摘要"""
    global num_requests_since_last_check
    print("后台活动监控线程已启动。")
    cleanup_counter = 0  # 清理计数器
    
    while not stop_event.is_set():
        # 等待30秒，或者直到 stop_event 被设置
        time.sleep(30)  # 每30秒打印一次
        if stop_event.is_set():
            break

        with request_counter_lock:
            current_request_count = num_requests_since_last_check
            num_requests_since_last_check = 0  # 重置计数器

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[{timestamp}] 服务器在线。过去30秒内处理请求数: {current_request_count}")
        
        # 每5分钟清理一次过期session（10个周期 * 30秒 = 5分钟）
        cleanup_counter += 1
        if cleanup_counter >= 10:
            try:
                cleaned_count = cleanup_expired_sessions()
                if cleaned_count > 0:
                    print(f"[{timestamp}] 清理了 {cleaned_count} 个过期的用户session")
            except Exception as e:
                logger.error(f"清理过期session时出错: {e}")
            cleanup_counter = 0


@app.before_request
def increment_request_count():
    """在每个请求之前增加请求计数器"""
    global num_requests_since_last_check
    with request_counter_lock:
        num_requests_since_last_check += 1


# --- Flask Routes ---
@app.route('/')
def index() -> tuple[Response, int] | Response:
    """Serve the main Vue app."""
    return jsonify({'error': 'Failed to serve application'}), 500


@app.route('/<path:path>')
def serve_vue_assets(path: str) -> tuple[Response, int] | Response:
    """Serve static assets for the Vue app."""
    try:
        dist_path = os.path.join(app.static_folder, '../frontend/dist')
        if path != "" and os.path.exists(os.path.join(dist_path, path)):
            return send_from_directory('../frontend/dist', path)
        return send_from_directory('../frontend/dist', 'index.html')
    except Exception as e:
        logger.error(f"Error serving static asset '{path}': {e}")
        return jsonify({'error': 'Failed to serve asset'}), 500


# --- 用户认证相关路由 ---
@app.route('/api/auth/register', methods=['POST'])
def api_register() -> tuple[Response, int] | Response:
    """用户注册"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少请求数据'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        invitation_code = data.get('invitation_code', '').strip()

        # 验证输入
        if not username or not password or not invitation_code:
            return jsonify({'success': False, 'error': '用户名、密码和邀请码都不能为空'}), 400

        if len(username) < 3 or len(username) > 20:
            return jsonify({'success': False, 'error': '用户名长度必须在3-20个字符之间'}), 400

        if len(password) < 6:
            return jsonify({'success': False, 'error': '密码长度至少6个字符'}), 400

        # 验证邀请码
        invitation_code_id = verify_invitation_code(invitation_code)
        if not invitation_code_id:
            return jsonify({'success': False, 'error': '邀请码无效或已过期'}), 400

        # 创建用户
        result = create_user(username, password, invitation_code_id)
        
        if result['success']:
            logger.info(f"User registered successfully: {username}")
            return jsonify({
                'success': True,
                'message': '注册成功！请登录。'
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'success': False, 'error': '注册过程中发生错误'}), 500


@app.route('/api/auth/login', methods=['POST'])
def api_login() -> tuple[Response, int] | Response:
    """用户登录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '缺少请求数据'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '').strip()

        if not username or not password:
            return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

        # 验证用户
        result = authenticate_user(username, password)
        
        if result['success']:
            # 设置session
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            session.permanent = True
            
            # 登录时加载历史session数据
            load_session_from_db()
            
            # 刷新session时间戳
            refresh_user_session()
            
            logger.info(f"User logged in successfully: {username}")
            return jsonify({
                'success': True,
                'message': '登录成功',
                'user': {
                    'user_id': result['user_id'],
                    'username': result['username']
                }
            })
        else:
            return jsonify({'success': False, 'error': result['error']}), 400

    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'success': False, 'error': '登录过程中发生错误'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def api_logout() -> tuple[Response, int] | Response:
    """用户登出"""
    try:
        if session.get('user_id'):
            username = session.get('username', 'Unknown')
            clear_user_session()  # 使用新的清除函数
            logger.info(f"User logged out: {username}")
            return jsonify({'success': True, 'message': '登出成功'})
        else:
            return jsonify({'success': False, 'error': '用户未登录'}), 400

    except Exception as e:
        logger.error(f"Logout error: {e}")
        return jsonify({'success': False, 'error': '登出过程中发生错误'}), 500


@app.route('/api/auth/user', methods=['GET'])
@login_required
def api_get_user_info() -> tuple[Response, int] | Response:
    """获取当前登录用户信息"""
    try:
        user_id = session.get('user_id')
        user_info = get_user_info(user_id)
        
        if user_info:
            return jsonify({
                'success': True,
                'user': {
                    'user_id': user_info['user_id'],
                    'username': user_info['username'],
                    'is_enabled': user_info['is_enabled'],
                    'created_at': user_info['created_at'].isoformat() if user_info['created_at'] else None
                }
            })
        else:
            session.clear()  # 清除无效session
            return jsonify({'success': False, 'error': '用户信息不存在'}), 404

    except Exception as e:
        logger.error(f"Get user info error: {e}")
        return jsonify({'success': False, 'error': '获取用户信息失败'}), 500


@app.route('/api/auth/check', methods=['GET'])
def api_check_auth() -> tuple[Response, int] | Response:
    """检查用户登录状态"""
    try:
        if session.get('user_id'):
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': {
                    'user_id': session.get('user_id'),
                    'username': session.get('username')
                }
            })
        else:
            return jsonify({
                'success': True,
                'authenticated': False
            })

    except Exception as e:
        logger.error(f"Check auth error: {e}")
        return jsonify({'success': False, 'error': '检查登录状态失败'}), 500


@app.route('/api/file_options', methods=['GET'])
@login_required
def api_file_options() -> tuple[Response, int] | Response:
    """Get available question bank files with progress information."""
    subjects_data: Dict[str, List[Dict[str, Any]]] = {}

    if not os.path.exists(SUBJECT_DIRECTORY) or not APP_WIDE_QUESTION_DATA:
        message = f"'{SUBJECT_DIRECTORY}' directory does not exist or no question banks available."
        logger.warning(message)
        return jsonify({'subjects': {}, 'message': message}), 200

    try:
        # 获取当前会话的练习信息
        current_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
        current_progress = None
        if current_file:
            current_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
            current_index = get_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
            initial_total = get_safe_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
            correct_first_try = get_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
            round_number = get_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
            
            if current_indices and initial_total > 0:
                current_progress = {
                    'current_question': current_index + 1,
                    'total_questions': len(current_indices),
                    'initial_total': initial_total,
                    'correct_first_try': correct_first_try,
                    'round_number': round_number,
                    'progress_percent': min(100, (current_index / len(current_indices)) * 100) if current_indices else 0
                }

        for filepath, questions_list in APP_WIDE_QUESTION_DATA.items():
            try:
                path_parts = normalize_filepath(filepath).split('/')

                if len(path_parts) < 2:
                    logger.warning(f"Invalid path format: '{filepath}'")
                    continue

                filename_with_ext = path_parts[-1]
                display_name = filename_with_ext.replace('.xlsx', '').replace('.xls', '')

                if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY:
                    subject_name = path_parts[1]
                elif len(path_parts) == 2 and path_parts[0] == SUBJECT_DIRECTORY:
                    subject_name = "未分类"
                else:
                    subject_name = "未知科目"

                if subject_name not in subjects_data:
                    subjects_data[subject_name] = []

                file_info = {
                    'key': filepath,
                    'display': display_name,
                    'count': len(questions_list) if isinstance(questions_list, list) else 0
                }

                # 添加进度信息
                if current_file == filepath and current_progress:
                    file_info['progress'] = current_progress
                else:
                    file_info['progress'] = None

                subjects_data[subject_name].append(file_info)

            except Exception as e:
                logger.error(f"Error processing file path '{filepath}': {e}")
                continue

        if not subjects_data:
            return jsonify({'subjects': {}, 'message': 'No question banks available.'}), 200

        # Sort subjects and files
        sorted_subjects_data = {
            subject: sorted(files, key=lambda x: x['display'])
            for subject, files in sorted(subjects_data.items())
        }

        return jsonify({'subjects': sorted_subjects_data})

    except Exception as e:
        logger.error(f"Error getting file options: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/start_practice', methods=['POST'])
@login_required
def api_start_practice() -> tuple[Response, int] | Response:
    """Start a new practice session."""
    try:
        data = request.get_json()
        if not data:
            logger.error("Missing request data")
            raise BadRequest("Missing request data")

        subject_name = data.get('subject')
        file_name = data.get('fileName')
        force_restart = data.get('force_restart', False)  # 添加强制重启参数
        shuffle_questions = data.get('shuffle_questions', True)  # 添加题目打乱参数，默认为True

        logger.info(
            f"Starting practice with subject: {subject_name}, file: {file_name}, force_restart: {force_restart}, shuffle_questions: {shuffle_questions}")

        if not subject_name or not file_name:
            logger.error("Missing subject name or file name")
            raise BadRequest("Missing subject name or file name")

        selected_file_path = file_name

        if selected_file_path not in APP_WIDE_QUESTION_DATA:
            logger.error(f"File path '{selected_file_path}' not found in question bank.")
            logger.error(f"Available files: {list(APP_WIDE_QUESTION_DATA.keys())}")
            raise NotFound("Selected question bank not found")

        current_question_bank = APP_WIDE_QUESTION_DATA[selected_file_path]
        if not isinstance(current_question_bank, list) or not current_question_bank:
            logger.error(f"Invalid or empty question bank: '{selected_file_path}'")
            return jsonify({'message': 'Selected question bank is empty or invalid.', 'success': False}), 400

        # 检查是否已有相同文件的活跃会话
        existing_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
        existing_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'])

        if not force_restart and existing_file == selected_file_path and existing_indices:
            logger.info(f"Resuming existing practice session for file: {selected_file_path}")
            return jsonify({
                'message': 'Resumed existing practice session.',
                'success': True,
                'resumed': True
            })

        # 开始新的练习会话
        question_indices = list(range(len(current_question_bank)))
        
        # 根据shuffle_questions参数决定是否打乱题目顺序
        if shuffle_questions:
            random.shuffle(question_indices)
            logger.info(f"Questions shuffled for random practice")
        else:
            logger.info(f"Questions kept in sequential order")

        # 清除旧的 session 数据并设置新的
        set_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'], selected_file_path)
        set_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], question_indices)
        set_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        set_safe_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        set_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        set_safe_session_value(SESSION_KEYS['INITIAL_TOTAL'], len(question_indices))
        set_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
        
        # 初始化题目状态数组，所有题目初始状态为未作答(0)
        question_statuses = [QUESTION_STATUS['UNANSWERED']] * len(question_indices)
        set_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], question_statuses)
        
        # 初始化答题历史字典
        answer_history = {}
        set_safe_session_value(SESSION_KEYS['ANSWER_HISTORY'], answer_history)

        practice_mode = "乱序练习" if shuffle_questions else "顺序练习"
        return jsonify({
            'message': f'Practice started successfully in {practice_mode} mode.',
            'success': True,
            'resumed': False
        })

    except BadRequest as e:
        logger.error(f"Bad Request in start_practice: {str(e)}")
        return jsonify({'message': str(e), 'success': False}), 400
    except NotFound as e:
        logger.error(f"Not Found in start_practice: {str(e)}")
        return jsonify({'message': str(e), 'success': False}), 404
    except Exception as e:
        logger.error(f"Error starting practice: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'message': 'Internal server error', 'success': False}), 500


@app.route('/api/practice/question', methods=['GET'])
def api_practice_question() -> Response:
    """Get the current practice question."""
    try:
        selected_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
        if not selected_file or selected_file not in APP_WIDE_QUESTION_DATA:
            raise BadRequest("No question bank selected or session expired")

        current_question_bank = APP_WIDE_QUESTION_DATA[selected_file]
        if not isinstance(current_question_bank, list):
            session.clear()
            raise BadRequest(f"Question bank data is invalid or corrupted")

        q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'])
        if not q_indices:
            raise NotFound("No questions available or session expired")

        current_idx = get_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        flash_messages = []

        if current_idx >= len(q_indices):
            wrong_indices = get_safe_session_value(SESSION_KEYS['WRONG_INDICES'], [])
            if not wrong_indices:
                return jsonify({'redirect_to_completed': True, 'message': 'Practice completed!',
                                'flash_messages': flash_messages})

            # Start new round with wrong questions
            new_round_indices = list(wrong_indices)
            random.shuffle(new_round_indices)
            set_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], new_round_indices)
            set_safe_session_value(SESSION_KEYS['WRONG_INDICES'], [])
            set_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
            round_number = get_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) + 1
            set_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], round_number)
            
            # 重置新轮次的题目状态数组
            new_question_statuses = [QUESTION_STATUS['UNANSWERED']] * len(new_round_indices)
            set_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], new_question_statuses)
            
            # 重置新轮次的答题历史
            new_answer_history = {}
            set_safe_session_value(SESSION_KEYS['ANSWER_HISTORY'], new_answer_history)

            flash_messages.append({
                'category': 'info',
                'text': f"Starting round {round_number} with {len(new_round_indices)} incorrect questions!"
            })

            current_idx = 0
            q_indices = new_round_indices

        if not q_indices:
            return jsonify({
                'redirect_to_completed': True,
                'message': 'All questions completed.',
                'flash_messages': flash_messages
            })

        question_index = q_indices[current_idx]
        if question_index >= len(current_question_bank):
            session.clear()
            raise BadRequest(f"Question index out of range")

        question_obj = current_question_bank[question_index]
        question_for_api = {
            'id': question_obj['id'],
            'type': question_obj['type'],
            'question': question_obj['question'],
            'options_for_practice': question_obj.get('options_for_practice'),
            'answer': question_obj['answer'],
            'is_multiple_choice': question_obj.get('is_multiple_choice', False)
        }

        progress = {
            'current': current_idx + 1,
            'total': len(q_indices),
            'round': get_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        }

        return jsonify({
            'question': question_for_api,
            'progress': progress,
            'flash_messages': flash_messages
        })

    except BadRequest as e:
        return jsonify({'message': str(e), 'question': None}), 400
    except NotFound as e:
        return jsonify({'message': str(e), 'question': None}), 404
    except Exception as e:
        logger.error(f"Error getting practice question: {e}")
        return jsonify({'message': 'Internal server error', 'question': None}), 500


class Question:
    def __init__(self, question_text, answer, options=None, question_type="选择题"):
        self.question_text = question_text
        self.answer = answer.upper()  # 统一转换为大写
        self.options = options
        self.type = question_type
        self.is_multiple_choice = len(self.answer) > 1  # 如果答案长度大于1，则为多选题

    def to_dict(self):
        return {
            "id": str(id(self)),  # 使用对象的id作为唯一标识
            "type": self.type,
            "question": self.question_text,
            "options_for_practice": self.options,
            "answer": self.answer if session.get('show_answers', False) else None,
            "is_multiple_choice": self.is_multiple_choice
        }


def validate_answer(user_answer: str, correct_answer: str, is_multiple_choice: bool) -> bool:
    """
    验证用户答案是否正确
    Args:
        user_answer: 用户提交的答案
        correct_answer: 正确答案
        is_multiple_choice: 是否为多选题
    Returns:
        bool: 答案是否正确
    """
    # 统一转换为大写
    user_answer = user_answer.upper()
    correct_answer = correct_answer.upper()

    if is_multiple_choice:
        # 多选题：答案需要完全匹配，顺序不重要
        user_choices = set(user_answer)
        correct_choices = set(correct_answer)
        return user_choices == correct_choices
    else:
        # 单选题或判断题：直接比较
        return user_answer == correct_answer


@app.route('/api/practice/submit', methods=['POST'])
def submit_answer() -> Response:
    """Submit an answer for the current question."""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")

        user_answer = data.get('answer', '').upper()
        question_id = data.get('question_id')
        peeked = data.get('peeked', False)  # 是否查看了答案
        is_review = data.get('is_review', False)  # 是否是复习模式

        # 保存用户答案到session，供答题历史使用
        session['last_user_answer'] = user_answer

        if not question_id:
            raise BadRequest("Question ID missing")

        selected_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
        if not selected_file or selected_file not in APP_WIDE_QUESTION_DATA:
            raise BadRequest("Invalid session or question bank")

        current_question_bank = APP_WIDE_QUESTION_DATA[selected_file]
        q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
        current_idx = get_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

        if current_idx >= len(q_indices):
            raise BadRequest("No more questions available")

        question_index = q_indices[current_idx]
        question_data = current_question_bank[question_index]

        is_multiple_choice = question_data.get('is_multiple_choice', False)
        correct_answer = question_data['answer'].upper()

        # 如果是查看答案，直接标记为错误
        is_correct = False if peeked else validate_answer(user_answer, correct_answer, is_multiple_choice)

        # 格式化答案显示
        options = question_data.get('options_for_practice', {})
        user_answer_display = '未作答（直接查看答案）' if peeked else format_answer_display(user_answer, options,
                                                                                          is_multiple_choice)
        correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

        feedback = {
            "is_correct": is_correct,
            "user_answer_display": user_answer_display,
            "correct_answer_display": correct_answer_display,
            "question_id": question_id,
            "current_index": current_idx
        }

        if not is_review:
            # 更新练习记录
            update_practice_record(question_data, is_correct, peeked)

        return jsonify(feedback)

    except BadRequest as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error submitting answer: {e}")
        return jsonify({'message': 'Internal server error'}), 500


def format_answer_display(answer: str, options: dict, is_multiple_choice: bool) -> str:
    """
    格式化答案显示
    """
    if not options:
        return answer

    if is_multiple_choice:
        # 多选题显示格式：A. 选项1 + B. 选项2
        formatted_answers = []
        for letter in sorted(answer):
            if letter in options:
                formatted_answers.append(f"{letter}. {options[letter]}")
        return " + ".join(formatted_answers)
    else:
        # 单选题显示格式：A. 选项1
        return f"{answer}. {options.get(answer, '')}" if answer in options else answer


def update_practice_record(question, is_correct: bool, peeked: bool):
    """
    更新练习记录
    Args:
        question: Question对象
        is_correct: 是否回答正确
        peeked: 是否查看了答案
    """
    selected_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
    if not selected_file or selected_file not in APP_WIDE_QUESTION_DATA:
        return

    current_question_bank = APP_WIDE_QUESTION_DATA[selected_file]
    if not isinstance(current_question_bank, list):
        return

    q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
    current_idx = get_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)

    if current_idx >= len(q_indices):
        return

    actual_question_master_index = q_indices[current_idx]

    # 更新题目状态
    question_statuses = get_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
    if len(question_statuses) == len(q_indices):
        # 确保状态数组长度正确
        if is_correct and not peeked:
            question_statuses[current_idx] = QUESTION_STATUS['CORRECT']
        else:
            question_statuses[current_idx] = QUESTION_STATUS['WRONG']
        set_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], question_statuses)

    # 保存答题历史 - 修复：确保使用一致的键名格式
    answer_history = get_safe_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
    history_key = str(current_idx)  # 使用题目在当前轮次中的索引作为key
    
    history_data = {
        'user_answer': session.get('last_user_answer', ''),
        'is_correct': is_correct,
        'peeked': peeked,
        'question_data': question
    }
    
    answer_history[history_key] = history_data
    set_safe_session_value(SESSION_KEYS['ANSWER_HISTORY'], answer_history)

    # 如果是查看答案或答错，添加到错题集
    if not is_correct or peeked:
        wrong_indices = get_safe_session_value(SESSION_KEYS['WRONG_INDICES'], [])
        if actual_question_master_index not in wrong_indices:
            wrong_indices.append(actual_question_master_index)
            set_safe_session_value(SESSION_KEYS['WRONG_INDICES'], wrong_indices)
    else:  # 答对且没有查看答案
        if get_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1) == 1:
            correct_first_try = get_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0) + 1
            set_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], correct_first_try)

    # 移动到下一题
    set_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], current_idx + 1)
    session.modified = True


@app.route('/api/completed_summary', methods=['GET'])
def api_completed_summary() -> tuple[Response, int] | Response:
    """Get the practice session summary."""
    try:
        initial_total = get_safe_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
        correct_first_try = get_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
        score_percent = (correct_first_try / initial_total * 100) if initial_total > 0 else 0

        completed_filename = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'], 'Unknown Question Bank')
        completed_filename_display = completed_filename.replace('.xlsx', '').replace('.xls', '')

        summary_data = {
            'initial_total': initial_total,
            'correct_first_try': correct_first_try,
            'score_percent': score_percent,
            'completed_filename': completed_filename_display
        }

        # 清理练习相关的session数据，但保留用户登录信息
        user_id = session.get('user_id')
        username = session.get('username')
        
        # 清除练习相关的session数据（只清理Cookie，不操作数据库）
        practice_keys = [
            SESSION_KEYS['CURRENT_EXCEL_FILE'],
            SESSION_KEYS['QUESTION_INDICES'],
            SESSION_KEYS['CURRENT_INDEX'],
            SESSION_KEYS['WRONG_INDICES'],
            SESSION_KEYS['ROUND_NUMBER'],
            SESSION_KEYS['INITIAL_TOTAL'],
            SESSION_KEYS['CORRECT_FIRST_TRY'],
            SESSION_KEYS['QUESTION_STATUSES'],
            SESSION_KEYS['ANSWER_HISTORY']
        ]
        
        for key in practice_keys:
            session.pop(key, None)
        
        # 恢复用户信息
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
        
        session.modified = True

        return jsonify({
            'summary': summary_data,
            'flash_messages': []
        })

    except Exception as e:
        logger.error(f"Error getting completed summary: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@app.route('/api/practice/jump', methods=['GET'])
def jump_to_question() -> tuple[Response, int] | Response:
    """Jump to a specific question in the practice session."""
    try:
        target_index = request.args.get('index')
        if not target_index:
            raise BadRequest("No target index provided")

        try:
            target_index = int(target_index)
        except ValueError:
            raise BadRequest("Invalid index format")

        if target_index < 0:
            raise BadRequest("Invalid question index")

        q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
        if not q_indices or target_index >= len(q_indices):
            raise BadRequest("Question index out of range")

        set_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], target_index)
        return jsonify({"message": "Successfully jumped to question", "success": True})

    except BadRequest as e:
        return jsonify({'message': str(e)}), 400
    except Exception as e:
        logger.error(f"Error jumping to question: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@app.route('/api/session/status', methods=['GET'])
def api_session_status() -> tuple[Response, int] | Response:
    """Check current session status."""
    try:
        selected_file = get_safe_session_value(SESSION_KEYS['CURRENT_EXCEL_FILE'])
        q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'])
        current_idx = get_safe_session_value(SESSION_KEYS['CURRENT_INDEX'], 0)
        round_number = get_safe_session_value(SESSION_KEYS['ROUND_NUMBER'], 1)
        initial_total = get_safe_session_value(SESSION_KEYS['INITIAL_TOTAL'], 0)
        correct_first_try = get_safe_session_value(SESSION_KEYS['CORRECT_FIRST_TRY'], 0)
        wrong_indices = get_safe_session_value(SESSION_KEYS['WRONG_INDICES'], [])

        if not selected_file or not q_indices or selected_file not in APP_WIDE_QUESTION_DATA:
            return jsonify({
                'active': False,
                'message': 'No active practice session'
            })

        current_question_bank = APP_WIDE_QUESTION_DATA[selected_file]
        if not isinstance(current_question_bank, list) or not current_question_bank:
            return jsonify({
                'active': False,
                'message': 'Invalid question bank data'
            })

        # 检查是否已经完成练习
        if current_idx >= len(q_indices) and not wrong_indices:
            return jsonify({
                'active': True,
                'completed': True,
                'message': 'Practice session completed'
            })

        # 提取文件名信息
        path_parts = normalize_filepath(selected_file).split('/')
        display_name = path_parts[-1].replace('.xlsx', '').replace('.xls', '')
        subject_name = path_parts[1] if len(path_parts) > 2 and path_parts[0] == SUBJECT_DIRECTORY else "未分类"

        return jsonify({
            'active': True,
            'completed': False,
            'file_info': {
                'key': selected_file,
                'display': display_name,
                'subject': subject_name
            },
            'progress': {
                'current': current_idx + 1,
                'total': len(q_indices),
                'round': round_number
            },
            'statistics': {
                'initial_total': initial_total,
                'correct_first_try': correct_first_try,
                'wrong_count': len(wrong_indices)
            },
            'question_statuses': get_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
        })

    except Exception as e:
        logger.error(f"Error checking session status: {e}")
        return jsonify({
            'active': False,
            'message': 'Error checking session status'
        }), 500


@app.route('/api/session/save', methods=['GET'])
@login_required
def api_save_session() -> tuple[Response, int] | Response:
    """Save current session progress to database."""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User not authenticated'
            }), 401

        # 获取当前session数据
        session_data = {}
        for key in SESSION_KEYS.values():
            if key in session:
                session_data[key] = session[key]

        if not session_data:
            return jsonify({
                'success': True,
                'message': 'No session data to save'
            })

        # 保存到数据库
        success = save_user_session(user_id, session_data)
        
        if success:
            logger.info(f"Session data saved to database for user {user_id}")
            return jsonify({
                'success': True,
                'message': 'Session saved successfully'
            })
        else:
            logger.error(f"Failed to save session data for user {user_id}")
            return jsonify({
                'success': False,
                'message': 'Failed to save session'
            }), 500

    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@app.route('/api/questions/<question_id>/analysis', methods=['GET'])
def api_question_analysis(question_id: str) -> tuple[Response, int] | Response:
    """Get analysis for a specific question."""
    try:
        # 从question_id中提取文件路径和索引
        if '_' not in question_id:
            return jsonify({
                'success': False,
                'message': 'Invalid question ID format'
            }), 400

        # question_id格式: filepath_index
        parts = question_id.rsplit('_', 1)
        if len(parts) != 2:
            return jsonify({
                'success': False,
                'message': 'Invalid question ID format'
            }), 400

        filepath = parts[0]
        try:
            question_index = int(parts[1])
        except ValueError:
            return jsonify({
                'success': False,
                'message': 'Invalid question index in ID'
            }), 400

        # 检查文件是否存在
        if filepath not in APP_WIDE_QUESTION_DATA:
            return jsonify({
                'success': False,
                'message': 'Question bank not found'
            }), 404

        current_question_bank = APP_WIDE_QUESTION_DATA[filepath]
        if not isinstance(current_question_bank, list) or question_index >= len(current_question_bank):
            return jsonify({
                'success': False,
                'message': 'Question not found'
            }), 404

        question_data = current_question_bank[question_index]

        # 返回题目解析（如果有的话）
        response_data = {
            'success': True,
            'question_id': question_id,
            'analysis': question_data.get('analysis', '暂无解析'),
            'knowledge_points': question_data.get('knowledge_points', [])
        }

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting question analysis: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@app.route('/api/practice/history/<int:question_index>', methods=['GET'])
def get_question_history(question_index: int) -> tuple[Response, int] | Response:
    """Get the answer history for a specific question."""
    try:
        q_indices = get_safe_session_value(SESSION_KEYS['QUESTION_INDICES'], [])
        logger.info(f"Getting history for question index {question_index}, q_indices length: {len(q_indices)}")
        
        if question_index < 0 or question_index >= len(q_indices):
            logger.warning(f"Invalid question index {question_index}, valid range: 0-{len(q_indices)-1}")
            return jsonify({
                'success': False,
                'message': f'Invalid question index. Valid range: 0-{len(q_indices)-1}'
            }), 400

        answer_history = get_safe_session_value(SESSION_KEYS['ANSWER_HISTORY'], {})
        history_key = str(question_index)
        
        logger.info(f"Looking for history with key '{history_key}', available keys: {list(answer_history.keys())}")
        
        if history_key not in answer_history:
            logger.warning(f"No history found for question index {question_index} (key: '{history_key}')")
            
            # 尝试获取题目状态，看是否确实应该有历史记录
            question_statuses = get_safe_session_value(SESSION_KEYS['QUESTION_STATUSES'], [])
            if question_index < len(question_statuses):
                status = question_statuses[question_index]
                logger.info(f"Question {question_index} status: {status}")
                
                if status != QUESTION_STATUS['UNANSWERED']:
                    logger.error(f"Question {question_index} marked as answered (status: {status}) but no history found!")
            
            return jsonify({
                'success': False,
                'message': 'No history found for this question'
            }), 404

        history_data = answer_history[history_key]
        question_data = history_data['question_data']
        
        logger.info(f"Found history for question {question_index}: correct={history_data['is_correct']}, "
                   f"peeked={history_data['peeked']}, user_answer='{history_data['user_answer']}'")
        
        # 格式化答案显示
        options = question_data.get('options_for_practice', {})
        is_multiple_choice = question_data.get('is_multiple_choice', False)
        correct_answer = question_data['answer'].upper()
        user_answer = history_data['user_answer']
        
        if history_data['peeked']:
            user_answer_display = '未作答（直接查看答案）'
        else:
            user_answer_display = format_answer_display(user_answer, options, is_multiple_choice)
        
        correct_answer_display = format_answer_display(correct_answer, options, is_multiple_choice)

        response_data = {
            'success': True,
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
        }
        
        logger.info(f"Successfully returned history for question {question_index}")
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting question history for index {question_index}: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


if __name__ == '__main__':
    # Create subject directory if it doesn't exist
    if not os.path.exists(SUBJECT_DIRECTORY):
        os.makedirs(SUBJECT_DIRECTORY)
        logger.info(f"Created '{SUBJECT_DIRECTORY}' directory")

    # Configure Werkzeug logger
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.ERROR)

    # Start activity monitoring thread
    activity_thread = threading.Thread(target=print_activity_periodically, daemon=True)
    activity_thread.start()

    HOST = '127.0.0.1'
    PORT = 5051
    
    logger.info(f"Flask application starting on http://{HOST}:{PORT}")
    
    try:
        # 方案1: 使用 Gunicorn (推荐，需要安装: pip install gunicorn)
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
                'workers': 4,  # 根据CPU核心数调整
                'worker_class': 'sync',  # 可选: gevent, eventlet
                'worker_connections': 1000,
                'timeout': 30,
                'keepalive': 2,
                'max_requests': 1000,
                'max_requests_jitter': 100,
                'preload_app': True,
                'accesslog': '-',
                'errorlog': '-',
                'loglevel': 'info'
            }
            
            logger.info("Using Gunicorn server for high performance")
            StandaloneApplication(app, options).run()
            
        except ImportError:
            # 方案2: 使用 Waitress (纯Python，需要安装: pip install waitress)
            try:
                from waitress import serve
                logger.info("Gunicorn not available！！, using Waitress server")
                serve(app, host=HOST, port=PORT, threads=6)
                
            except ImportError:
                # 方案3: 使用 Flask 开发服务器（多线程模式）
                logger.warning("High-performance servers not available, using Flask dev server with threading")
                app.run(host=HOST, port=PORT, debug=False, threaded=True, processes=1)
                
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, closing server...")
    finally:
        logger.info("Stopping background thread...")
        stop_event.set()
        if activity_thread.is_alive():
            activity_thread.join(timeout=5)
        logger.info("Background thread stopped. Server shutdown complete.")
