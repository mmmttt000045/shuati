import mysql.connector
from mysql.connector import Error
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json  # 添加json导入用于session数据序列化

def connect_and_validate_mysql(host_name, user_name, user_password, db_name, target_username_to_check=None):
    """
    连接到云服务器上的 MySQL 数据库并进行一些验证。

    参数:
    host_name (str): 数据库服务器主机名或 IP 地址。
    user_name (str): MySQL 用户名。
    user_password (str): MySQL 用户密码。
    db_name (str): 要连接的数据库名称。
    target_username_to_check (str, optional): 要在 user_accounts 表中检查的用户名。
    """
    connection = None
    cursor = None
    try:
        # 建立连接
        # 强烈建议为生产环境启用 SSL/TLS 加密连接
        # connection_config = {
        #     'host': host_name,
        #     'user': user_name,
        #     'password': user_password,
        #     'database': db_name,
        #     'port': 3306,  # 默认端口，如果更改了请修改
        #     'ssl_ca': '/path/to/ca.pem',
        #     'ssl_cert': '/path/to/client-cert.pem',
        #     'ssl_key': '/path/to/client-key.pem',
        #     'ssl_verify_cert': True
        # }
        # connection = mysql.connector.connect(**connection_config)

        # 不使用 SSL 的简单连接 (不推荐用于生产环境的敏感数据传输)
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            password=user_password,
            database=db_name,
            port=3306  # 默认端口，如果更改了请修改
        )

        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"成功连接到 MySQL 服务器！版本: {db_info}")

            cursor = connection.cursor()

            # 验证 1: 查询数据库版本 (更详细)
            cursor.execute("SELECT version();")
            record = cursor.fetchone()
            print(f"数据库版本是: {record[0]}")

            # 验证 2: 判断特定用户是否存在并可用 (假设你有上一节课的 user_accounts 表)
            if target_username_to_check:
                query_user = "SELECT username, is_enabled FROM user_accounts WHERE username = %s"
                cursor.execute(query_user, (target_username_to_check,))
                user_record = cursor.fetchone()

                if user_record:
                    username, is_enabled = user_record
                    status = "启用" if is_enabled else "禁用"
                    print(f"验证判断: 用户 '{username}' 存在，状态为: {status}。")
                else:
                    print(f"验证判断: 用户 '{target_username_to_check}' 不存在。")
            else:
                # 验证 3: 如果不检查特定用户，可以尝试查询表中的记录数
                cursor.execute("SELECT COUNT(*) FROM user_accounts;") # 替换为你的表名
                count_record = cursor.fetchone()
                print(f"表 user_accounts 中共有 {count_record[0]} 条记录。")


            return True # 表示连接和基本验证成功

    except Error as e:
        print(f"连接 MySQL 或执行查询时出错: {e}")
        # 常见的错误代码和原因:
        # 1045: Access denied for user 'xxx'@'xxx' (用户名、密码或来源 IP 错误/权限不足)
        # 2003: Can't connect to MySQL server on 'xxx' (主机名/IP错误、端口不通、防火墙阻止、MySQL服务未运行)
        # 1146: Table 'xxx.yyy' doesn't exist (表名或数据库名错误)
        return False # 表示连接或验证失败
    finally:
        # 关闭数据库连接
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
            print("MySQL 连接已关闭。")

def get_db_connection():
    """获取数据库连接"""
    try:
        connection = mysql.connector.connect(
            host="14.103.133.62",
            user="shuati",
            password="fxTWMaTLFyMMcKfh",
            database="shuati",
            port=3306
        )
        return connection
    except Error as e:
        print(f"数据库连接错误: {e}")
        return None

def hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_invitation_code(invitation_code: str) -> Optional[int]:
    """
    验证邀请码是否有效
    返回邀请码ID，如果无效返回None
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        # 检查邀请码是否存在、未使用且未过期
        query = """
        SELECT id FROM invitation_codes 
        WHERE code = %s AND is_used = FALSE 
        AND (expires_at IS NULL OR expires_at > NOW())
        """
        cursor.execute(query, (invitation_code,))
        result = cursor.fetchone()
        
        if result:
            return result[0]  # 返回邀请码ID
        return None
        
    except Error as e:
        print(f"验证邀请码时出错: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def create_user(username: str, password: str, invitation_code_id: int) -> Dict[str, Any]:
    """
    创建新用户
    返回包含成功/失败信息的字典
    """
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM user_accounts WHERE username = %s", (username,))
        if cursor.fetchone():
            return {"success": False, "error": "用户名已存在"}
        
        # 对密码进行哈希处理
        password_hash = hash_password(password)
        
        # 开始事务
        connection.start_transaction()
        
        # 插入新用户
        insert_user_query = """
        INSERT INTO user_accounts (username, password_hash, used_invitation_code_id)
        VALUES (%s, %s, %s)
        """
        cursor.execute(insert_user_query, (username, password_hash, invitation_code_id))
        user_id = cursor.lastrowid
        
        # 标记邀请码为已使用
        update_invitation_query = """
        UPDATE invitation_codes 
        SET is_used = TRUE, used_by_user_id = %s 
        WHERE id = %s
        """
        cursor.execute(update_invitation_query, (user_id, invitation_code_id))
        
        # 提交事务
        connection.commit()
        
        return {
            "success": True, 
            "user_id": user_id,
            "message": "用户创建成功"
        }
        
    except Error as e:
        # 回滚事务
        connection.rollback()
        print(f"创建用户时出错: {e}")
        return {"success": False, "error": f"创建用户失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """
    验证用户登录
    返回包含用户信息或错误信息的字典
    """
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
        # 查询用户信息
        query = """
        SELECT id, username, password_hash, is_enabled 
        FROM user_accounts 
        WHERE username = %s
        """
        cursor.execute(query, (username,))
        user_record = cursor.fetchone()
        
        if not user_record:
            return {"success": False, "error": "用户名或密码错误"}
        
        user_id, db_username, stored_password_hash, is_enabled = user_record
        
        # 检查账户是否启用
        if not is_enabled:
            return {"success": False, "error": "账户已被禁用"}
        
        # 验证密码
        input_password_hash = hash_password(password)
        if input_password_hash != stored_password_hash:
            return {"success": False, "error": "用户名或密码错误"}
        
        return {
            "success": True,
            "user_id": user_id,
            "username": db_username,
            "message": "登录成功"
        }
        
    except Error as e:
        print(f"用户认证时出错: {e}")
        return {"success": False, "error": f"登录失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    """
    根据用户ID获取用户信息
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        query = """
        SELECT id, username, is_enabled, created_at 
        FROM user_accounts 
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        user_record = cursor.fetchone()
        
        if user_record:
            user_id, username, is_enabled, created_at = user_record
            return {
                "user_id": user_id,
                "username": username,
                "is_enabled": is_enabled,
                "created_at": created_at
            }
        return None
        
    except Error as e:
        print(f"获取用户信息时出错: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def create_invitation_code(code: str, expires_days: Optional[int] = None) -> Dict[str, Any]:
    """
    创建邀请码
    """
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
        # 检查邀请码是否已存在
        cursor.execute("SELECT id FROM invitation_codes WHERE code = %s", (code,))
        if cursor.fetchone():
            return {"success": False, "error": "邀请码已存在"}
        
        # 计算过期时间
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
        # 插入邀请码
        insert_query = """
        INSERT INTO invitation_codes (code, expires_at)
        VALUES (%s, %s)
        """
        cursor.execute(insert_query, (code, expires_at))
        connection.commit()
        
        return {
            "success": True,
            "code": code,
            "expires_at": expires_at,
            "message": "邀请码创建成功"
        }
        
    except Error as e:
        print(f"创建邀请码时出错: {e}")
        return {"success": False, "error": f"创建邀请码失败: {str(e)}"}
    finally:
        if connection.is_connected():
            connection.close()

# ============ 用户Session管理相关函数 ============

def save_user_session(user_id: int, session_data: Dict[str, Any]) -> bool:
    """
    保存用户的session数据到数据库
    
    Args:
        user_id: 用户ID
        session_data: session数据字典
        
    Returns:
        bool: 保存是否成功
    """
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        # 将session数据序列化为JSON
        session_json = json.dumps(session_data, ensure_ascii=False, default=str)
        
        # 使用REPLACE INTO来插入或更新session数据
        query = """
        REPLACE INTO user_sessions (user_id, session_data, updated_at)
        VALUES (%s, %s, NOW())
        """
        cursor.execute(query, (user_id, session_json))
        connection.commit()
        
        return True
        
    except Error as e:
        print(f"保存用户session时出错: {e}")
        return False
    except (TypeError, ValueError) as e:
        print(f"序列化session数据时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def load_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    从数据库加载用户的session数据
    
    Args:
        user_id: 用户ID
        
    Returns:
        Optional[Dict[str, Any]]: session数据字典，如果不存在或加载失败返回None
    """
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        
        query = """
        SELECT session_data, updated_at 
        FROM user_sessions 
        WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        
        if result:
            session_json, updated_at = result
            
            # 检查session是否过期（2小时）
            if updated_at and datetime.now() - updated_at > timedelta(hours=2):
                # session已过期，删除它
                delete_user_session(user_id)
                return None
            
            # 反序列化JSON数据
            try:
                session_data = json.loads(session_json)
                return session_data
            except (json.JSONDecodeError, TypeError) as e:
                print(f"反序列化session数据时出错: {e}")
                return None
        
        return None
        
    except Error as e:
        print(f"加载用户session时出错: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def delete_user_session(user_id: int) -> bool:
    """
    删除用户的session数据
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 删除是否成功
    """
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        query = "DELETE FROM user_sessions WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        connection.commit()
        
        return True
        
    except Error as e:
        print(f"删除用户session时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def cleanup_expired_sessions() -> int:
    """
    清理过期的session数据（超过2小时）
    
    Returns:
        int: 清理的session数量
    """
    connection = get_db_connection()
    if not connection:
        return 0
    
    try:
        cursor = connection.cursor()
        
        # 删除2小时前的session
        query = """
        DELETE FROM user_sessions 
        WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """
        cursor.execute(query)
        connection.commit()
        
        return cursor.rowcount
        
    except Error as e:
        print(f"清理过期session时出错: {e}")
        return 0
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def update_session_timestamp(user_id: int) -> bool:
    """
    更新用户session的时间戳（用于延长session生命周期）
    
    Args:
        user_id: 用户ID
        
    Returns:
        bool: 更新是否成功
    """
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        
        query = """
        UPDATE user_sessions 
        SET updated_at = NOW() 
        WHERE user_id = %s
        """
        cursor.execute(query, (user_id,))
        connection.commit()
        
        return cursor.rowcount > 0
        
    except Error as e:
        print(f"更新session时间戳时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

if __name__ == "__main__":
    # --- 请根据你的云服务器 MySQL 配置修改以下变量 ---
    DB_HOST = "14.103.133.62"  # 例如: "120.79.xxx.xxx" 或 "mysql.example.com"
    DB_USER = "shuati"                  # 例如: "app_user"
    DB_PASSWORD = "fxTWMaTLFyMMcKfh"            # 你的 MySQL 用户密码
    DB_NAME = "shuati"               # 例如: "mydatabase"
    USERNAME_TO_VERIFY = "testuser"             # 要检查的用户名，例如你之前创建的表中的用户


    print("尝试连接到 MySQL 数据库并进行验证...")
    if connect_and_validate_mysql(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, USERNAME_TO_VERIFY):
        print("MySQL 连接和验证成功！")
    else:
        print("MySQL 连接或验证失败。请检查配置和错误信息。")