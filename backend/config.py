"""
配置文件 - 包含所有常量和配置项
"""
from datetime import timedelta


# --- MySQL 数据库配置 ---
class DatabaseConfig:
    # MySQL 连接池配置
    MYSQL_POOL_CONFIG = {
        'pool_name': "mypool",
        'pool_size': 10,  # 连接池大小，可根据并发需求调整
        'pool_reset_session': True,  # 确保每次获取的连接状态是干净的
        'host': "14.103.133.62",
        'user': "shuati",
        'password': "fxTWMaTLFyMMcKfh",
        'database': "shuati",
        'port': 3306,
        'autocommit': True,  # 默认自动提交
        'charset': 'utf8mb4',
        'collation': 'utf8mb4_unicode_ci',
        'connect_timeout': 10,  # 连接超时时间(秒) - 增加到30秒
        'use_unicode': True,  # 使用Unicode
        'auth_plugin': 'mysql_native_password',  # 指定认证插件
        'sql_mode': 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
    }

    # 连接重试配置
    CONNECTION_RETRY_CONFIG = {
        'max_retries': 3,
        'retry_delay': 1,  # 秒
        'backoff_factor': 2
    }


# --- Redis 配置 ---
class RedisConfig:
    """Redis 连接和session存储配置"""
    # Redis 连接配置
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 0
    SESSION_DB =1
    REDIS_PASSWORD = None  # 如果Redis设置了密码
    REDIS_DECODE_RESPONSES = False  # 设置为False避免UTF-8解码问题，Flask-Session会自行处理编码

    # Redis 连接池配置
    REDIS_POOL_CONFIG = {
        'max_connections': 20,
        'retry_on_timeout': True,
        'socket_connect_timeout': 5,
        'socket_timeout': 5,
        'health_check_interval': 30
    }

    # Session 存储配置
    REDIS_SESSION_PREFIX = 'session:'
    REDIS_SESSION_TTL = 7200  # 2小时，与Flask session保持一致

    # Flask-Session 配置
    FLASK_SESSION_PREFIX = 'flask_session:'
    FLASK_SESSION_TTL = 7200  # 2小时
    FLASK_SESSION_KEY_PREFIX = 'session_'

    # 压缩配置
    ENABLE_COMPRESSION = True  # 启用数据压缩以节省内存
    COMPRESSION_THRESHOLD = 1024  # 大于1KB的数据才压缩


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
# 核心会话密钥，按功能分组
SESSION_KEYS = {
    # 用户身份相关
    'USER_ID': 'user_id',  # 当前登录用户ID
    'USERNAME': 'username',  # 当前登录用户名
    'USER_MODEL': 'user_model',  # 用户权限模型

    # 练习状态相关
    'CURRENT_TIKU_ID': 'current_tiku_id',  # 当前练习的题库ID
    'SELECT_TYPES': 'select_types',
    'QUESTION_INDICES': 'q_indices_to_practice',  # 当前轮次需要练习的题目索引列表
    'CURRENT_INDEX': 'current_idx_in_indices_list',  # 当前题目在索引列表中的位置
    'WRONG_INDICES': 'wrong_q_indices_this_round',  # 本轮答错的题目索引列表

    # 练习统计相关
    'ROUND_NUMBER': 'round_number',  # 当前练习轮次
    'INITIAL_TOTAL': 'initial_total_questions',  # 初始题目总数
    'CORRECT_FIRST_TRY': 'correct_on_first_try',  # 第一轮答对的题目数量

    # 题目状态相关
    'QUESTION_STATUSES': 'question_answer_statuses',  # 每道题的答题状态数组
    'ANSWER_HISTORY': 'question_answer_history',  # 每道题的答题历史记录
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

    # Flask-Session 配置 - 使用Redis存储session数据
    SESSION_TYPE = 'redis'  # 使用Redis存储session
    SESSION_REDIS = None  # 这将在应用初始化时设置
    SESSION_PERMANENT = True
    SESSION_USE_SIGNER = True  # 启用session签名
    SESSION_KEY_PREFIX = 'session_'  # session key前缀
    SESSION_ID_LENGTH = 32  # session ID长度
    
    # Session Cookie 配置 - 优化的2小时过期机制
    # 优化: 现在只有session ID存储在cookie中, session数据存储在Redis中
    SESSION_COOKIE_SECURE = False  # Development setting
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_NAME = 'quiz_session'
    SESSION_COOKIE_DOMAIN = None
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # 2小时过期
    SESSION_COOKIE_MAX_AGE = 7200  # 2小时的秒数
    SESSION_REFRESH_EACH_REQUEST = True  # 每次请求都刷新session
    
    # Session活跃度管理配置
    SESSION_ACTIVITY_THRESHOLD = timedelta(minutes=30)  # 30分钟无活动警告阈值
    SESSION_WARNING_MINUTES = 10  # 过期前10分钟警告
    SESSION_CLEANUP_INTERVAL = 300  # 5分钟清理一次过期session

    # CORS 配置
    CORS_ORIGINS = ["*"]
    CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
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
