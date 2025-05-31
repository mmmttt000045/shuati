# MT题库练习系统

一个基于 Flask 和 Vue 3 构建的现代化在线题库练习系统，支持多端同步、高性能部署和智能练习模式。

## ✨ 主要特性

### 核心功能
- 🎯 **多题型支持**：单选题、多选题、判断题
- 📊 **智能进度跟踪**：实时记录练习进度和成绩
- 🔄 **多轮练习模式**：错题自动加入下一轮复习
- 📱 **多端同步**：支持跨设备无缝切换
- 🎲 **灵活练习模式**：支持乱序和顺序两种练习方式
- 📈 **详细统计分析**：答题历史、正确率统计

### 高级功能
- 👥 **用户认证系统**：注册、登录、邀请码机制
- 💾 **自动进度保存**：实时保存练习状态，防止数据丢失
- 🖥️ **现代化界面**：响应式设计，支持移动端
- ⚡ **高性能部署**：支持 Gunicorn、Waitress 等生产级服务器
- 🎨 **答题卡界面**：直观显示题目状态，支持快速跳转

## 🏗️ 项目结构

```
MT题库练习系统/
├── app.py                          # Flask 后端主程序
├── connectDB.py                    # 数据库连接和操作
├── start_server.py                # 高性能服务器启动脚本
├── init_database.py               # 数据库初始化脚本
├── requirements.txt               # Python 依赖
├── frontend/                      # Vue 3 前端
│   ├── src/
│   │   ├── components/           # Vue 组件
│   │   │   ├── IndexPage.vue    # 题库选择页面
│   │   │   ├── PracticePage.vue # 练习页面
│   │   │   ├── CompletedPage.vue# 完成页面
│   │   │   └── LoginPage.vue    # 登录页面
│   │   ├── router/              # 路由配置
│   │   ├── services/            # API 服务
│   │   ├── stores/              # 状态管理
│   │   └── types/               # TypeScript 类型定义
│   ├── package.json
│   └── vite.config.ts
├── subject/                       # 题库 Excel 文件目录
│   └── [科目名称]/
│       └── [题库文件].xlsx
├── templates/                     # Flask 模板
└── 文档/
    ├── README_session_optimization.md  # Session 优化说明
    ├── README_多端同步.md              # 多端同步功能说明
    ├── SERVER_GUIDE.md                # 高性能服务器部署指南
    └── ANSWER_CARD_FIX_GUIDE.md       # 答题卡修复指南
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Node.js 16+
- MySQL 5.7+

### 1. 克隆项目
```bash
git clone <repository-url>
cd shuati
```

### 2. 后端设置

#### 创建虚拟环境
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

#### 安装依赖
```bash
pip install -r requirements.txt
```

#### 数据库初始化
```bash
# 配置数据库连接（编辑 connectDB.py）
python init_database.py
```

### 3. 前端设置
```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. 启动应用

#### 方式一：自动选择最佳服务器（推荐）
```bash
python start_server.py
```

#### 方式二：指定服务器类型
```bash
# 使用 Gunicorn（Linux/Mac 推荐）
python start_server.py --server gunicorn --workers 4

# 使用 Waitress（Windows 推荐）
python start_server.py --server waitress --threads 8

# 自定义端口
python start_server.py --port 8080
```

#### 方式三：开发模式
```bash
python app.py
```

应用将在 `http://127.0.0.1:5051` 启动

## 📚 题库配置

### Excel 文件格式要求

在 `subject/` 目录下按科目创建文件夹，每个科目包含对应的 Excel 题库文件：

```
subject/
├── Java基础/
│   ├── 语法基础.xlsx
│   └── 面向对象.xlsx
├── 数据结构/
│   ├── 线性表.xlsx
│   └── 树和图.xlsx
└── 算法/
    └── 排序算法.xlsx
```

### Excel 表格列名要求

| 列名 | 必需 | 说明 |
|------|------|------|
| 题干 | ✅ | 题目内容 |
| 答案 | ✅ | 正确答案（A/B/C/D 或 T/F） |
| 题型 | ❌ | 题目类型（自动识别） |
| A | ❌ | 选项A（选择题必需） |
| B | ❌ | 选项B（选择题必需） |
| C | ❌ | 选项C（选择题可选） |
| D | ❌ | 选项D（选择题可选） |

### 题型说明

1. **单选题**：答案为单个字母（如：A）
2. **多选题**：答案为多个字母（如：AB、ABC）
3. **判断题**：答案为 T/F、正确/错误、对/错等

## 🔧 高级配置

### 服务器性能优化

#### Gunicorn 配置（Linux 生产环境）
```bash
# 创建配置文件
cat > gunicorn.conf.py << EOF
bind = "0.0.0.0:5051"
workers = 4
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
preload_app = True
EOF

# 启动
gunicorn --config gunicorn.conf.py app:app
```

#### Waitress 配置（Windows 生产环境）
```bash
python start_server.py --server waitress --host 0.0.0.0 --port 5051 --threads 8
```

### 多端同步配置

系统支持用户在多个设备间同步练习进度：

1. **登录同步**：用户登录时自动加载历史进度
2. **实时保存**：每次答题后自动保存到数据库
3. **智能恢复**：切换设备时无缝恢复练习状态

### Session 管理优化

系统采用优化的 Session 管理策略：

- **Cookie + 数据库混合模式**：平时使用 Cookie，关键时刻同步数据库
- **数字状态编码**：使用数字而非字符串存储状态，节省 80% 内存
- **智能同步时机**：登录时加载，登出时保存，减少数据库压力

## 🔌 API 接口

### 认证相关
- `POST /api/auth/register` - 用户注册
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/logout` - 用户登出
- `GET /api/auth/check` - 检查登录状态

### 题库管理
- `GET /api/file_options` - 获取可用题库列表
- `POST /api/start_practice` - 开始练习
- `GET /api/session/status` - 获取当前会话状态
- `GET /api/session/save` - 保存当前进度

### 练习相关
- `GET /api/practice/question` - 获取当前题目
- `POST /api/practice/submit` - 提交答案
- `GET /api/practice/jump?index=<n>` - 跳转到指定题目
- `GET /api/practice/history/<index>` - 获取答题历史
- `GET /api/completed_summary` - 获取练习总结

### 题目分析
- `GET /api/questions/<id>/analysis` - 获取题目解析

## 🛠️ 开发指南

### 前端开发
```bash
cd frontend
npm run dev          # 开发服务器
npm run build        # 生产构建
npm run type-check   # 类型检查
```

### 后端开发
```bash
python app.py        # 启动开发服务器
python -m pytest    # 运行测试（如果有）
```

### 数据库管理
```bash
python init_database.py    # 初始化数据库
python create_test_invitation.py  # 创建测试邀请码
```

## 📊 性能监控

应用内置性能监控功能：

- **请求统计**：每 30 秒输出请求处理数量
- **Session 清理**：每 5 分钟自动清理过期 Session
- **错误日志**：详细记录错误信息到 `quiz_app.log`

监控输出示例：
```
[2024-01-01 12:00:00] 服务器在线。过去30秒内处理请求数: 15
[2024-01-01 12:05:00] 清理了 3 个过期的用户session
```

## 🔍 故障排除

### 常见问题

#### 1. 数据库连接失败
```bash
# 检查配置
vim connectDB.py
# 检查 MySQL 服务
systemctl status mysql
```

#### 2. 端口被占用
```bash
# 查看端口占用
netstat -tulpn | grep :5051
# 使用其他端口
python start_server.py --port 8080
```

#### 3. 前端构建失败
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

#### 4. Session 数据不同步
- 确保用户已登录
- 检查数据库连接
- 查看服务器日志 `quiz_app.log`

### 日志分析
系统日志保存在 `quiz_app.log`，包含：
- 用户登录/登出记录
- API 请求错误
- 数据库操作异常
- Session 同步状态

## 🚀 生产部署

### 使用 systemd（Linux）
```bash
# 创建服务文件
sudo vim /etc/systemd/system/quiz-app.service

[Unit]
Description=MT Quiz Application
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/shuati
ExecStart=/path/to/venv/bin/python start_server.py --server gunicorn --host 0.0.0.0
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target

# 启用服务
sudo systemctl enable quiz-app
sudo systemctl start quiz-app
```

### 使用 Docker
```dockerfile
# Dockerfile 示例
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN cd frontend && npm install && npm run build

EXPOSE 5051
CMD ["python", "start_server.py", "--host", "0.0.0.0"]
```

### Nginx 反向代理
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5051;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 📈 性能基准

| 服务器类型 | 并发能力 | 内存使用 | 适用场景 |
|------------|----------|----------|----------|
| Flask Dev | ~50 | 低 | 开发测试 |
| Waitress | ~500 | 中等 | 中小规模部署 |
| Gunicorn | ~1000+ | 中等 | 生产环境首选 |
| Gevent | ~5000+ | 低 | 高并发场景 |

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [Vue 3](https://vuejs.org/) - 渐进式前端框架
- [Vite](https://vitejs.dev/) - 现代化构建工具
- [TypeScript](https://www.typescriptlang.org/) - 类型安全的 JavaScript

---

**Made with ❤️ by MingTai**

如果这个项目对你有帮助，请给个 ⭐️ 支持一下！ 