# 多端同步功能使用说明

## 功能概述

现在您的刷题应用支持**多端同步**功能！这意味着：

- ✅ 同一个账号可以在多个设备上登录
- ✅ 刷题进度在所有设备间实时同步
- ✅ 在手机上做题，在电脑上继续，无缝切换
- ✅ 答题历史、错题集、练习状态完全同步

## 技术原理

### 之前的方式
- Session数据存储在浏览器Cookie中
- 每个设备都有独立的Session
- 无法跨设备同步进度

### 现在的方式
- Session数据存储在MySQL数据库中
- 基于用户ID管理Session
- 所有设备共享同一个Session数据

## 安装步骤

### 1. 运行数据库初始化脚本

```bash
python init_database.py
```

这个脚本会：
- 检查数据库连接状态
- 创建`user_sessions`表
- 创建自动清理过期Session的存储过程

### 2. 验证安装

运行脚本后，您应该看到类似输出：

```
=== 数据库初始化脚本 ===
这个脚本将创建user_sessions表以支持多端同步session功能

1. 检查数据库状态...
✅ user_sessions表已存在
📋 user_sessions表结构:
   - id: int(11)
   - user_id: int(11)
   - session_data: json
   - created_at: timestamp
   - updated_at: timestamp

2. 创建user_sessions表...
✅ user_sessions表创建成功
✅ CleanupExpiredSessions存储过程创建成功

✅ 数据库初始化完成！
现在您可以启动应用程序，享受多端同步的刷题体验。
```

## 使用说明

### 多端登录
1. 在设备A上登录您的账号
2. 开始刷题，做几道题目
3. 在设备B上用同一个账号登录
4. 您会发现刷题进度完全同步！

### 同步的内容
- ✅ 当前选择的题库文件
- ✅ 题目练习顺序
- ✅ 当前练习到第几题
- ✅ 答错的题目列表
- ✅ 练习轮次信息
- ✅ 每道题的答题状态
- ✅ 答题历史记录
- ✅ 首次答对的题目统计

### 自动同步时机
- 登录时：自动加载服务器上的Session数据
- 答题时：每次提交答案后自动保存到服务器
- 切换题目时：实时同步当前进度
- 访问任何页面时：刷新Session有效期

## 技术细节

### 数据库表结构

```sql
CREATE TABLE user_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_session (user_id),
    FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE,
    INDEX idx_updated_at (updated_at)
);
```

### Session过期机制
- Session有效期：2小时
- 自动刷新：每次访问时刷新有效期
- 自动清理：服务器每5分钟清理过期的Session

### 数据一致性
- 读取：优先从数据库读取，本地Session作为备份
- 写入：同时写入数据库和本地Session
- 冲突：以数据库中的数据为准

## 故障排除

### 问题：数据库初始化失败
```
❌ 数据库连接失败
```
**解决方案：**
1. 检查`connectDB.py`中的数据库连接配置
2. 确认MySQL服务器正在运行
3. 验证网络连接

### 问题：Session数据不同步
**可能原因：**
1. 用户未登录（只有登录用户的Session才会同步）
2. 数据库连接问题
3. JSON序列化错误

**解决方案：**
1. 确保在所有设备上都已登录
2. 检查服务器日志中的错误信息
3. 重新登录账号

### 问题：Session过期太快
**解决方案：**
修改`connectDB.py`中的过期时间：

```python
# 在load_user_session函数中
if updated_at and datetime.now() - updated_at > timedelta(hours=4):  # 改为4小时
```

## 性能优化

### 1. 数据库连接池
如果用户量大，建议使用连接池：

```python
# 在connectDB.py中添加
from mysql.connector import pooling

config = {
    'host': '14.103.133.62',
    'user': 'shuati',
    'password': 'fxTWMaTLFyMMcKfh',
    'database': 'shuati',
    'pool_name': 'mypool',
    'pool_size': 10
}

pool = pooling.MySQLConnectionPool(**config)
```

### 2. Redis缓存
对于高并发场景，可以考虑使用Redis：

```python
# 可选：使用Redis作为Session存储
import redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)
```

## 安全考虑

### 1. Session数据加密
Session数据以JSON格式存储，包含练习进度等信息，不包含敏感信息。

### 2. 用户隔离
每个用户的Session数据完全隔离，通过user_id进行区分。

### 3. 自动清理
过期Session会自动清理，避免数据库膨胀。

## 向后兼容

- ✅ 已有用户无需任何操作
- ✅ 未登录用户仍然可以使用本地Session
- ✅ 登录后自动升级为多端同步

升级完成后，享受无缝的多端刷题体验吧！🎉 