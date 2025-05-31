#!/usr/bin/env python3
"""
高性能 Flask 应用启动脚本
支持多种服务器类型和配置选项
"""

import argparse
import os
import sys
from app import app, logger, stop_event, activity_thread, print_activity_periodically
import threading

def start_with_gunicorn(host='127.0.0.1', port=5051, workers=4, worker_class='sync'):
    """使用 Gunicorn 启动服务器"""
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
            'bind': f'{host}:{port}',
            'workers': workers,
            'worker_class': worker_class,
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
        
        logger.info(f"Starting Gunicorn server with {workers} {worker_class} workers")
        StandaloneApplication(app, options).run()
        return True
        
    except ImportError:
        logger.error("Gunicorn not installed. Install with: pip install gunicorn")
        return False

def start_with_waitress(host='127.0.0.1', port=5051, threads=6):
    """使用 Waitress 启动服务器"""
    try:
        from waitress import serve
        logger.info(f"Starting Waitress server with {threads} threads")
        serve(app, host=host, port=port, threads=threads)
        return True
        
    except ImportError:
        logger.error("Waitress not installed. Install with: pip install waitress")
        return False

def start_with_gevent(host='127.0.0.1', port=5051):
    """使用 Gevent 启动服务器"""
    try:
        from gevent.pywsgi import WSGIServer
        logger.info("Starting Gevent server")
        http_server = WSGIServer((host, port), app)
        http_server.serve_forever()
        return True
        
    except ImportError:
        logger.error("Gevent not installed. Install with: pip install gevent")
        return False

def start_with_flask_dev(host='127.0.0.1', port=5051, debug=False):
    """使用 Flask 开发服务器（多线程模式）"""
    logger.info("Starting Flask development server with threading")
    app.run(host=host, port=port, debug=debug, threaded=True, processes=1)
    return True

def main():
    parser = argparse.ArgumentParser(description='启动高性能 Flask 应用服务器')
    parser.add_argument('--server', '-s', 
                      choices=['gunicorn', 'waitress', 'gevent', 'flask'],
                      default='auto',
                      help='选择服务器类型 (默认: auto - 自动选择最佳可用服务器)')
    parser.add_argument('--host', default='127.0.0.1', help='绑定的主机地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', '-p', type=int, default=5051, help='端口号 (默认: 5051)')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Gunicorn worker 数量 (默认: 4)')
    parser.add_argument('--worker-class', choices=['sync', 'gevent', 'eventlet'], 
                      default='sync', help='Gunicorn worker 类型 (默认: sync)')
    parser.add_argument('--threads', '-t', type=int, default=6, help='Waitress 线程数 (默认: 6)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式 (仅用于 Flask 开发服务器)')
    
    args = parser.parse_args()
    
    # 检查端口是否被占用
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((args.host, args.port))
    sock.close()
    if result == 0:
        logger.error(f"Port {args.port} is already in use")
        sys.exit(1)
    
    # 创建主题目录
    SUBJECT_DIRECTORY = 'subject'
    if not os.path.exists(SUBJECT_DIRECTORY):
        os.makedirs(SUBJECT_DIRECTORY)
        logger.info(f"Created '{SUBJECT_DIRECTORY}' directory")
    
    # 启动活动监控线程
    activity_thread = threading.Thread(target=print_activity_periodically, daemon=True)
    activity_thread.start()
    
    logger.info(f"Starting server on http://{args.host}:{args.port}")
    
    try:
        if args.server == 'auto':
            # 自动选择最佳可用服务器
            success = (start_with_gunicorn(args.host, args.port, args.workers, args.worker_class) or
                      start_with_waitress(args.host, args.port, args.threads) or
                      start_with_flask_dev(args.host, args.port, args.debug))
        elif args.server == 'gunicorn':
            success = start_with_gunicorn(args.host, args.port, args.workers, args.worker_class)
        elif args.server == 'waitress':
            success = start_with_waitress(args.host, args.port, args.threads)
        elif args.server == 'gevent':
            success = start_with_gevent(args.host, args.port)
        elif args.server == 'flask':
            success = start_with_flask_dev(args.host, args.port, args.debug)
        
        if not success:
            logger.error("Failed to start any server")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, closing server...")
    finally:
        logger.info("Stopping background thread...")
        stop_event.set()
        if activity_thread.is_alive():
            activity_thread.join(timeout=5)
        logger.info("Server shutdown complete.")

if __name__ == '__main__':
    main() 