# API 配置说明

## 环境变量配置

本项目使用 Vite 环境变量来管理 API 基地址，你可以通过以下方式配置：

### 1. 创建环境变量文件

在 `frontend/` 目录下创建以下文件之一：

- `.env` - 所有环境通用
- `.env.local` - 本地环境（会被 git 忽略）
- `.env.development` - 开发环境
- `.env.production` - 生产环境

### 2. 设置 API 基地址

在环境变量文件中添加：

```bash
# API 基地址配置
VITE_API_BASE_URL=http://127.0.0.1:5051/api
```

### 3. 环境示例

#### 开发环境 (.env.development)
```bash
VITE_API_BASE_URL=http://127.0.0.1:5051/api
```

#### 生产环境 (.env.production)
```bash
VITE_API_BASE_URL=https://your-api-domain.com/api
```

### 4. 重要说明

1. **必须以 `VITE_` 开头** - 只有以 `VITE_` 开头的环境变量才能在客户端使用
2. **重启开发服务器** - 修改环境变量后需要重启 `npm run dev` 才能生效
3. **默认值** - 如果没有设置环境变量，系统会使用默认值 `http://127.0.0.1:5051/api`

### 5. 当前配置

系统启动时会在控制台输出当前的 API 配置信息，你可以通过浏览器开发者工具查看。

### 6. 配置文件位置

API 配置统一管理在 `src/config/api.ts` 文件中，包含：

- API 基地址
- 认证 API 地址
- 超时配置
- 重试配置
- 日志配置

如需修改其他配置项，请直接编辑该文件。 