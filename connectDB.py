import mysql.connector
from mysql.connector import Error
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

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
    except Error:
        return None

def hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_invitation_code(invitation_code: str) -> Optional[int]:
    """验证邀请码是否有效，返回邀请码ID"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        query = """
        SELECT id FROM invitation_codes 
        WHERE code = %s AND is_used = FALSE 
        AND (expires_at IS NULL OR expires_at > NOW())
        """
        cursor.execute(query, (invitation_code,))
        result = cursor.fetchone()
        return result[0] if result else None
        
    except Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def create_user(username: str, password: str, invitation_code_id: int) -> Dict[str, Any]:
    """创建新用户"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM user_accounts WHERE username = %s", (username,))
        if cursor.fetchone():
            return {"success": False, "error": "用户名已存在"}
        
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
        
        connection.commit()
        return {"success": True, "user_id": user_id, "message": "用户创建成功"}
        
    except Error as e:
        connection.rollback()
        return {"success": False, "error": f"创建用户失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def authenticate_user(username: str, password: str) -> Dict[str, Any]:
    """验证用户登录"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
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
        
        if not is_enabled:
            return {"success": False, "error": "账户已被禁用"}
        
        input_password_hash = hash_password(password)
        if input_password_hash != stored_password_hash:
            return {"success": False, "error": "用户名或密码错误"}

        query ="UPDATE user_accounts SET last_time_login = NOW() WHERE id = %s;"
        cursor.execute(query, (user_id,))
        
        return {
            "success": True,
            "user_id": user_id,
            "username": db_username,
            "message": "登录成功"
        }
        
    except Error as e:
        return {"success": False, "error": f"登录失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def get_user_model(user_id: int) -> Optional[int]:
    """获取用户模式 0是普通用户 5是vip用户 10是root用户"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        query = """
        SELECT model
        FROM user_accounts
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        return result[0] if result else 0  # 默认返回0（普通用户）
        
    except Error:
        return 0  # 发生错误时返回普通用户身份
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def get_user_info(user_id: int) -> Optional[Dict[str, Any]]:
    """根据用户ID获取用户信息"""
    connection = get_db_connection()
    if not connection:
        return None
    
    try:
        cursor = connection.cursor()
        query = """
        SELECT id, username, is_enabled, created_at, model 
        FROM user_accounts 
        WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        user_record = cursor.fetchone()
        
        if user_record:
            user_id, username, is_enabled, created_at, model = user_record
            return {
                "user_id": user_id,
                "username": username,
                "is_enabled": is_enabled,
                "created_at": created_at,
                "model": model if model is not None else 0
            }
        return None
        
    except Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def create_invitation_code(code: str, expires_days: Optional[int] = None) -> Dict[str, Any]:
    """创建邀请码"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}
    
    try:
        cursor = connection.cursor()
        
        # 检查邀请码是否已存在
        cursor.execute("SELECT id FROM invitation_codes WHERE code = %s", (code,))
        if cursor.fetchone():
            return {"success": False, "error": "邀请码已存在"}
        
        expires_at = None
        if expires_days:
            expires_at = datetime.now() + timedelta(days=expires_days)
        
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
        return {"success": False, "error": f"创建邀请码失败: {str(e)}"}
    finally:
        if connection.is_connected():
            connection.close()

def save_user_session(user_id: int, session_data: Dict[str, Any]) -> bool:
    """保存用户的session数据到数据库"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        session_json = json.dumps(session_data, ensure_ascii=False, default=str)
        
        query = """
        REPLACE INTO user_sessions (user_id, session_data, updated_at)
        VALUES (%s, %s, NOW())
        """
        cursor.execute(query, (user_id, session_json))
        connection.commit()
        return True
        
    except (Error, TypeError, ValueError):
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def load_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库加载用户的session数据"""
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
                delete_user_session(user_id)
                return None
            
            try:
                return json.loads(session_json)
            except (json.JSONDecodeError, TypeError):
                return None
        
        return None
        
    except Error:
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def delete_user_session(user_id: int) -> bool:
    """删除用户的session数据"""
    connection = get_db_connection()
    if not connection:
        return False
    
    try:
        cursor = connection.cursor()
        query = "DELETE FROM user_sessions WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        connection.commit()
        return True
        
    except Error:
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def cleanup_expired_sessions() -> int:
    """清理过期的session数据（超过2小时）"""
    connection = get_db_connection()
    if not connection:
        return 0
    
    try:
        cursor = connection.cursor()
        query = """
        DELETE FROM user_sessions 
        WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR)
        """
        cursor.execute(query)
        connection.commit()
        return cursor.rowcount
        
    except Error:
        return 0
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def update_session_timestamp(user_id: int) -> bool:
    """更新用户session的时间戳"""
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
        
    except Error:
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

# 测试连接函数（仅在直接运行时使用）
def test_connection():
    """测试数据库连接"""
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"Database connection successful. Version: {version[0]}")
            return True
        except Error as e:
            print(f"Database query error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if connection.is_connected():
                connection.close()
    else:
        print("Failed to connect to database")
        return False

if __name__ == "__main__":
    test_connection()