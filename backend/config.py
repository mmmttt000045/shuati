"""
配置文件 - 包含所有常量和配置项
"""
import os
from datetime import timedelta

# --- 配置 ---
SUBJECT_DIRECTORY = 'subject'  # 科目目录
SHEET_NAME = 0  # Excel工作表名

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

# --- Flask 配置 ---
class Config:
    SECRET_KEY = 'your-fixed-secret-key-here'
    
    # Session 配置
    SESSION_COOKIE_SECURE = False  # Development setting
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'quiz_session'
    SESSION_COOKIE_DOMAIN = None
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_MAX_AGE = 7200  # 2小时的秒数
    SESSION_REFRESH_EACH_REQUEST = True
    
    # CORS 配置
    CORS_ORIGINS = ["*"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    CORS_HEADERS = ["Content-Type", "Authorization", "Accept", "Origin",
                    "X-Requested-With", "Cache-Control", "Pragma"]
    CORS_SUPPORTS_CREDENTIALS = True

# --- 服务器配置 ---
class ServerConfig:
    HOST = '127.0.0.1'
    PORT = 5051
    
    # Gunicorn 配置
    GUNICORN_OPTIONS = {
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
    
    # Waitress 配置
    WAITRESS_OPTIONS = {
        'threads': 6,
        'connection_limit': 100,
        'cleanup_interval': 30,
        'channel_timeout': 120
    } 