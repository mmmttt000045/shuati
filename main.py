"""
主应用文件 - 整合所有模块
"""
import logging
import os
import sys
import threading
import time

from flask import Flask, send_from_directory, session, request
from flask_cors import CORS
from flask_session import Session

# 导入backend模块
from backend.config import Config, ServerConfig
from backend.connectDB import (
    init_connection_pool, cleanup_expired_practice_sessions, batch_update_tiku_usage
)
from backend.routes.admin import admin_bp
from backend.routes.auth import auth_bp
from backend.routes.practice import practice_bp, usage_stats_lock,  tiku_usage_stats,cache_manager
from backend.routes.profile import profile_bp
from backend.routes.usage import usage_bp

from backend.session_manager import SessionManager
from backend.utils import create_response

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

# 全局变量
request_counter = 0
request_counter_lock = threading.Lock()
stop_event = threading.Event()


def sync_usage_stats_to_database():
    """同步题库使用次数到数据库"""
    global tiku_usage_stats

    with usage_stats_lock:
        if not tiku_usage_stats:
            return

        # 复制当前统计数据并清空
        stats_to_sync = dict(tiku_usage_stats)
        tiku_usage_stats.clear()

    if stats_to_sync:
        try:
            result = batch_update_tiku_usage(stats_to_sync)
            if result['success']:
                total_updates = sum(stats_to_sync.values())
                logger.info(f"Synced usage stats: {len(stats_to_sync)} files, {total_updates} total usages")
            else:
                logger.error(f"Failed to sync usage stats: {result['error']}")
                # 如果同步失败，重新添加到统计中
                with usage_stats_lock:
                    for tiku_id, count in stats_to_sync.items():
                        tiku_usage_stats[tiku_id] = tiku_usage_stats.get(tiku_id, 0) + count
        except Exception as e:
            logger.error(f"Error in batch_update_tiku_usage: {e}")
            # 如果发生异常，重新添加到统计中
            with usage_stats_lock:
                for tiku_id, count in stats_to_sync.items():
                    tiku_usage_stats[tiku_id] = tiku_usage_stats.get(tiku_id, 0) + count


def monitor_activity():
    """后台活动监控 - 优化版本，包含session管理"""
    global request_counter
    cleanup_counter = 0
    session_cleanup_counter = 0

    while not stop_event.is_set():
        time.sleep(30)
        if stop_event.is_set():
            break

        with request_counter_lock:
            current_count = request_counter
            request_counter = 0

        logger.info(f"Server active. Requests in last 30s: {current_count}")

        cleanup_counter += 1
        session_cleanup_counter += 1

        # 每5分钟清理一次过期的练习会话
        if cleanup_counter >= 10:  # 每5分钟清理一次
            try:
                cleaned = cleanup_expired_practice_sessions()
                if cleaned > 0:
                    logger.info(f"Cleaned {cleaned} expired practice sessions")
            except Exception as e:
                logger.error(f"Error cleaning practice sessions: {e}")
            cleanup_counter = 0

        # 每10分钟的统计信息记录
        if session_cleanup_counter >= 20:  # 每10分钟
            try:
                logger.info("Session由Flask-Session自动管理，无需手动清理")
            except Exception as e:
                logger.error(f"Error in session status logging: {e}")
            session_cleanup_counter = 0

        # 同步题库使用次数到数据库
        try:
            sync_usage_stats_to_database()
        except Exception as e:
            logger.error(f"Error syncing usage stats: {e}")


# --- Flask App Initialization ---
def create_app():
    """创建Flask应用"""
    app = Flask(__name__, static_folder='frontend/dist')

    # 应用配置
    app.config.from_object(Config)
    app.config['SESSION_REDIS'] = SessionManager.create_session_redis()

    # 初始化 Flask-Session
    try:
        Session(app)
    except Exception as e:
        logger.error(f"Flask-Session初始化失败: {e}")
        # 如果初始化失败，使用默认的客户端session
        exit(-1)

    # 配置 CORS
    cors = CORS(app,
                resources={
                    r"/*": {
                        "origins": Config.CORS_ORIGINS,
                        "methods": Config.CORS_METHODS,
                        "allow_headers": Config.CORS_HEADERS,
                        "supports_credentials": Config.CORS_SUPPORTS_CREDENTIALS
                    }
                })

    # 先注册通用路由（SPA路由处理） - 必须在蓝图注册之前
    @app.route('/')
    @app.route('/<path:path>')
    def serve_app(path: str = ''):
        """服务前端应用 - SPA路由处理"""
        # 跳过API路由
        if path.startswith('api/'):
            # 让API路由由蓝图处理
            from flask import abort
            abort(404)
        
        try:
            # 检查是否是静态资源请求
            if path and '.' in path:  # 有扩展名的文件（如.js, .css, .ico等）
                static_file_path = os.path.join(app.static_folder, path)
                if os.path.exists(static_file_path):
                    return send_from_directory(app.static_folder, path)
                # 如果静态资源不存在，对于SPA应用也返回index.html让前端处理
                # 这样可以避免404错误，让前端路由器处理所有路径
                pass
            
            # 对于所有其他路径（前端路由），返回index.html
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.error(f"服务静态文件时出错: {e}")
            # 即使出错，也尝试返回index.html让前端处理
            try:
                return send_from_directory(app.static_folder, 'index.html')
            except:
                return create_response(False, 'Failed to serve application', status_code=500)[0]

    # 注册蓝图
    app.register_blueprint(auth_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(usage_bp)
    app.register_blueprint(profile_bp)

    @app.before_request
    def before_request():
        """请求前处理 - 简化版本，只统计请求"""
        global request_counter
        with request_counter_lock:
            request_counter += 1

        # 设置session为永久性
        session.permanent = True

    # 添加错误处理器来处理session相关错误
    @app.errorhandler(UnicodeDecodeError)
    def handle_unicode_error(e):
        """处理Unicode解码错误"""
        logger.error(f"Unicode解码错误: {e}")
        # 清空当前session
        session.clear()
        return create_response(False, 'Session数据损坏，已重置', status_code=400)[0]

    return app


if __name__ == '__main__':
    # 配置日志 - 确保日志可以在后台运行时正常工作
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

    # 初始化数据库连接池
    init_connection_pool()

    # 预热缓存 - 从数据库加载数据到缓存中
    logger.info("正在预热缓存...")
    try:
        cache_manager.refresh_all_cache()
        logger.info("缓存预热完成")
    except Exception as e:
        logger.error(f"缓存预热失败: {e}")

    # 启动后台监控线程
    activity_thread = threading.Thread(target=monitor_activity, daemon=True)
    activity_thread.start()

    # 创建Flask应用
    app = create_app()

    HOST = ServerConfig.HOST
    PORT = ServerConfig.PORT

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


            options = ServerConfig.GUNICORN_OPTIONS.copy()
            options['bind'] = f'{HOST}:{PORT}'

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
                      **ServerConfig.WAITRESS_OPTIONS)
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
