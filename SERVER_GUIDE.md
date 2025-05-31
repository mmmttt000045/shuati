# 高性能服务器使用指南

本应用已经从 `wsgiref.simple_server` 升级为支持多种高性能服务器。

## 🚀 推荐服务器选择

### 1. Gunicorn (推荐 - Linux/Mac)
- **最佳性能**：生产环境首选
- **多进程**：支持多个 worker 进程
- **稳定可靠**：经过大量生产环境验证

### 2. Waitress (推荐 - Windows/跨平台)
- **纯 Python**：无需编译，跨平台兼容性好
- **多线程**：高并发处理能力
- **易于部署**：特别适合 Windows 环境

### 3. Gevent (高并发场景)
- **异步处理**：基于协程的高并发
- **内存效率**：单进程处理大量连接
- **适合 I/O 密集型**：网络请求较多的场景

## 📦 安装依赖

```bash
# 安装所有推荐依赖
pip install -r requirements.txt

# 或者按需安装
pip install gunicorn        # Linux/Mac 推荐
pip install waitress        # Windows 推荐
pip install gevent          # 高并发场景
```

## 🛠️ 启动方式

### 方式1：使用原始 app.py (自动选择最佳服务器)
```bash
python app.py
```

### 方式2：使用专用启动脚本 (推荐)
```bash
# 自动选择最佳可用服务器
python start_server.py

# 指定使用 Gunicorn
python start_server.py --server gunicorn --workers 4

# 指定使用 Waitress
python start_server.py --server waitress --threads 8

# 指定使用 Gevent
python start_server.py --server gevent

# 自定义端口和主机
python start_server.py --host 0.0.0.0 --port 8080

# 查看所有选项
python start_server.py --help
```

### 方式3：直接使用命令行工具
```bash
# 使用 Gunicorn 命令行
gunicorn --bind 127.0.0.1:5051 --workers 4 app:app

# 使用 Waitress 命令行
waitress-serve --host 127.0.0.1 --port 5051 app:app
```

## ⚙️ 性能优化配置

### Gunicorn 配置优化
```bash
# CPU 密集型任务
python start_server.py --server gunicorn --workers 4 --worker-class sync

# I/O 密集型任务
python start_server.py --server gunicorn --workers 4 --worker-class gevent

# 高并发场景
python start_server.py --server gunicorn --workers 8 --worker-class gevent
```

### Waitress 配置优化
```bash
# 增加线程数处理更多并发
python start_server.py --server waitress --threads 12

# 生产环境推荐配置
python start_server.py --server waitress --threads 8 --host 0.0.0.0
```

## 🔧 生产环境部署建议

### 1. 使用 Gunicorn (Linux 服务器)
```bash
# 创建 gunicorn 配置文件
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5051"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
preload_app = True
EOF

# 启动服务
gunicorn --config gunicorn.conf.py app:app
```

### 2. 使用 Waitress (Windows 服务器)
```bash
# 生产环境启动
python start_server.py --server waitress --host 0.0.0.0 --port 5051 --threads 8
```

### 3. 使用 systemd 服务 (Linux)
```bash
# 创建服务文件
sudo nano /etc/systemd/system/quiz-app.service

# 服务文件内容
[Unit]
Description=Quiz App
After=network.target

[Service]
User=your-user
WorkingDirectory=/path/to/your/app
ExecStart=/path/to/python start_server.py --server gunicorn --host 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target

# 启用并启动服务
sudo systemctl enable quiz-app
sudo systemctl start quiz-app
```

## 📊 性能对比

| 服务器 | 并发能力 | 内存使用 | CPU 使用 | 适用场景 |
|--------|----------|----------|----------|----------|
| wsgiref | 极低 | 低 | 低 | 仅开发测试 |
| Gunicorn | 高 | 中等 | 中等 | 生产环境首选 |
| Waitress | 中高 | 中等 | 中等 | Windows/跨平台 |
| Gevent | 极高 | 低 | 低 | 高并发 I/O |

## 🐛 故障排除

### 端口被占用
```bash
# 查看端口占用
netstat -tulpn | grep :5051
# 或者
lsof -i :5051

# 杀死占用进程
kill -9 <PID>
```

### 依赖安装问题
```bash
# 升级 pip
pip install --upgrade pip

# 清理缓存重新安装
pip cache purge
pip install -r requirements.txt --force-reinstall
```

### 权限问题 (Linux)
```bash
# 如果需要绑定到 80 端口
sudo python start_server.py --port 80

# 或者使用 nginx 反向代理
```

## 📈 监控和日志

应用已内置请求监控，每 30 秒会输出服务器活动统计：
```
[2024-01-01 12:00:00] 服务器在线。过去30秒内处理请求数: 15
```

日志文件位置：`quiz_app.log` 