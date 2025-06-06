import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

from mysql.connector import Error
from mysql.connector import pooling

from backend.config import DatabaseConfig

logger = logging.getLogger(__name__)
db_pool = None


def init_connection_pool():
    global db_pool
    try:
        # 使用config.py中的配置参数
        db_pool = pooling.MySQLConnectionPool(**DatabaseConfig.MYSQL_POOL_CONFIG)
        print("数据库连接池创建成功")
    except Error as e:
        print(f"创建数据库连接池失败: {e}")
        exit(1)
        # 在这里处理初始化失败的情况，比如退出应用


def get_db_connection():
    """从连接池获取数据库连接"""
    global db_pool
    if db_pool is None:
        # 实际应用中，这里应该有更健壮的错误处理或重试逻辑
        # 或者确保 init_connection_pool() 已经被成功调用
        print("错误：连接池未初始化")
        # Consider raising an exception here or ensuring init_connection_pool is always called
        raise ConnectionError("Database connection pool not initialized.")
    try:
        # 从池中获取连接
        connection = db_pool.get_connection()
        return connection
    except Error as e:
        print(f"从连接池获取连接失败: {e}")
        # Consider raising an exception here
        raise ConnectionError(f"Failed to get connection from pool: {e}")


# New decorator for handling DB connection and cursor
def with_db_connection(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            # Assuming operations might want to manage transactions or need the connection
            # Pass cursor to the wrapped function. Adjust if connection also needed.
            # Using dictionary=True for cursor to get results as dicts, common for APIs.
            cursor = conn.cursor(dictionary=True) 
            result = func(cursor, *args, **kwargs)
            # If the function itself doesn't commit (e.g. for transactions spanning multiple calls),
            # this commit might be too broad. For now, assuming functions are atomic or manage their own commits.
            # If autocommit is True (as per DatabaseConfig.MYSQL_POOL_CONFIG default), this explicit commit is not strictly needed for SELECTs
            # but good for INSERT/UPDATE/DELETE if autocommit was False or transaction started.
            if conn.autocommit is False:
                 conn.commit()
            return result
        except Error as e:
            print(f"Database operation error in {func.__name__}: {e}")
            if conn and conn.autocommit is False:
                conn.rollback()
            # Propagate the error or return a standardized error structure
            # For now, re-raising to be handled by @handle_api_error or similar in routes
            raise  # Or return {"success": False, "error": str(e)} if that's the standard
        finally:
            if cursor:
                try:
                    cursor.close()
                except Error as e:
                    print(f"Error closing cursor: {e}")
            if conn and conn.is_connected():
                try:
                    conn.close() # Returns connection to the pool
                except Error as e:
                    print(f"Error closing connection: {e}")
    return wrapper


def hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


@with_db_connection
def verify_invitation_code(cursor, invitation_code: str) -> Optional[int]:
    """验证邀请码是否有效，返回邀请码ID"""
    # connection and cursor are now managed by the decorator
    # try/except/finally for connection/cursor is removed
    query = """
            SELECT id
            FROM invitation_codes
            WHERE code = %s
              AND is_used = 0
              AND (expires_at IS NULL OR expires_at > NOW())
            """
    cursor.execute(query, (invitation_code,))
    result = cursor.fetchone()
    return result['id'] if result else None # Access by key due to dictionary=True


def create_user(username: str, password: str, invitation_code_id: int) -> Dict[str, Any]:
    """创建新用户"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        # 确保连接的autocommit设置正确
        connection.autocommit = False
        cursor = connection.cursor(dictionary=True)

        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM user_accounts WHERE username = %s", (username,))
        if cursor.fetchone():
            return {"success": False, "error": "用户名已存在"}

        # 再次验证邀请码是否仍然有效（防止并发问题）
        cursor.execute("""
                       SELECT id
                       FROM invitation_codes
                       WHERE id = %s
                         AND is_used = 0
                         AND (expires_at IS NULL OR expires_at > NOW())
                       """, (invitation_code_id,))
        if not cursor.fetchone():
            return {"success": False, "error": "邀请码已失效或被使用"}

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
                                  SET is_used         = 1,
                                      used_by_user_id = %s,
                                      used_time       = NOW()
                                  WHERE id = %s
                                    AND is_used = 0
                                  """
        cursor.execute(update_invitation_query, (user_id, invitation_code_id))

        # 检查是否成功更新了邀请码
        if cursor.rowcount == 0:
            connection.rollback()
            return {"success": False, "error": "邀请码已被其他用户使用"}

        connection.commit()
        return {"success": True, "user_id": user_id, "message": "用户创建成功"}

    except Error as e:
        try:
            if connection:
                connection.rollback()
        except Error as ex_rollback: # Catch specific error for rollback
            print(f"Error during rollback: {ex_rollback}")
        return {"success": False, "error": f"创建用户失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.autocommit = True  # 恢复默认设置
                connection.close()
        except Error as ex_finally: # Catch specific error for finally block
            print(f"Error in finally block of create_user: {ex_finally}")


@with_db_connection
def authenticate_user(cursor, username: str, password: str) -> Dict[str, Any]:
    """验证用户登录"""
    # connection, cursor, try/except/finally are managed by the decorator
    query = """
            SELECT id, username, password_hash, is_enabled, model, email
            FROM user_accounts
            WHERE username = %s
            """ # Removed trailing backslash from query
    cursor.execute(query, (username,))
    user_record = cursor.fetchone()

    if not user_record:
        return {"success": False, "error": "用户名或密码错误"}

    # user_id, db_username, stored_password_hash, is_enabled = user_record # Unpacking from dict
    user_id = user_record['id']
    db_username = user_record['username']
    stored_password_hash = user_record['password_hash']
    is_enabled = user_record['is_enabled']
    model = user_record['model']
    email = user_record['email']

    if not is_enabled:
        return {"success": False, "error": "账户已被禁用"}

    input_password_hash = hash_password(password)
    if input_password_hash != stored_password_hash:
        return {"success": False, "error": "用户名或密码错误"}

    # Assuming autocommit is True or decorator handles commit for DML
    # If the decorator is set to commit on all successful operations, 
    # and autocommit is false, this update will be committed.
    # If autocommit is true (default in config), this will commit immediately.
    update_last_login_query = "UPDATE user_accounts SET last_time_login = NOW() WHERE id = %s"
    cursor.execute(update_last_login_query, (user_id,))

    return {
        "success": True,
        "user_id": user_id,
        "username": db_username,
        "model": model,
        "message": "登录成功",
        "email": email,
    }


@with_db_connection
def get_user_model(cursor, user_id: int) -> Optional[int]:
    """获取用户模式 0是普通用户 5是vip用户 10是root用户"""
    # connection, cursor, try/except/finally are managed by the decorator
    query = """
            SELECT model
            FROM user_accounts
            WHERE id = %s
            """ # Removed trailing backslash
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()
    # Original code returned 0 on error or if no result. 
    # The decorator will re-raise DB errors.
    # If user not found, result is None. If found, result is a dict e.g. {'model': 10}
    if result:
        return result['model']
    # Consider what to return if user_id not found. Defaulting to 0 as per original logic.
    # This case (user not found) is not a database Error, so decorator won't catch it as such.
    return 0 


@with_db_connection
def get_user_info(cursor, user_id: int) -> Optional[Dict[str, Any]]:
    """根据用户ID获取用户信息"""
    query = """
            SELECT id , username, is_enabled, created_at, model
            FROM user_accounts
            WHERE id = %s
            """ # Removed trailing backslash
    cursor.execute(query, (user_id,))
    user_record = cursor.fetchone() # Returns a dict or None

    if user_record:
        # Convert datetime to isoformat if needed for JSON serialization, done in routes/auth.py currently
        # user_record['created_at'] = user_record['created_at'].isoformat() if user_record['created_at'] else None
        return user_record # user_record is already a dictionary
    return None # User not found


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
                       VALUES (%s, %s) \
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


def cleanup_expired_practice_sessions() -> int:
    """清理过期的练习会话（超过24小时未更新的active状态会话）"""
    connection = get_db_connection()
    if not connection:
        return 0

    try:
        cursor = connection.cursor()
        query = """
        UPDATE practice_sessions 
        SET status = 'abandoned', updated_at = NOW()
        WHERE status = 'active' 
        AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
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


# 科目和题库管理相关函数
def get_all_subjects() -> list:
    """获取所有科目"""
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        query = """
                SELECT subject_id, subject_name, exam_time, created_at, updated_at
                FROM subject
                ORDER BY subject_name
                """
        cursor.execute(query)
        subjects = []
        for row in cursor.fetchall():
            subjects.append({
                'subject_id': row[0],
                'subject_name': row[1],
                'exam_time': row[2].isoformat() if row[2] else None,
                'created_at': row[3].isoformat() if row[3] else None,
                'updated_at': row[4].isoformat() if row[4] else None
            })
        return subjects

    except Error as e:
        print(f"Error getting subjects: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def create_subject(subject_name: str, exam_time: str = None) -> Dict[str, Any]:
    """创建新科目"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 检查科目名是否已存在
        cursor.execute("SELECT subject_id FROM subject WHERE subject_name = %s", (subject_name,))
        if cursor.fetchone():
            return {"success": False, "error": "科目名已存在"}

        # 插入新科目
        if exam_time:
            query = "INSERT INTO subject (subject_name, exam_time) VALUES (%s, %s)"
            cursor.execute(query, (subject_name, exam_time))
        else:
            query = "INSERT INTO subject (subject_name) VALUES (%s)"
            cursor.execute(query, (subject_name,))

        connection.commit()
        subject_id = cursor.lastrowid

        return {
            "success": True,
            "subject_id": subject_id,
            "message": "科目创建成功"
        }

    except Error as e:
        return {"success": False, "error": f"创建科目失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def update_subject(subject_id: int, subject_name: str, exam_time: str = None) -> Dict[str, Any]:
    """更新科目信息"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 检查科目是否存在
        cursor.execute("SELECT subject_id FROM subject WHERE subject_id = %s", (subject_id,))
        if not cursor.fetchone():
            return {"success": False, "error": "科目不存在"}

        # 检查新名称是否已被其他科目使用
        cursor.execute("SELECT subject_id FROM subject WHERE subject_name = %s AND subject_id != %s",
                       (subject_name, subject_id))
        if cursor.fetchone():
            return {"success": False, "error": "科目名已存在"}

        # 更新科目
        if exam_time:
            query = "UPDATE subject SET subject_name = %s, exam_time = %s WHERE subject_id = %s"
            cursor.execute(query, (subject_name, exam_time, subject_id))
        else:
            query = "UPDATE subject SET subject_name = %s, exam_time = NULL WHERE subject_id = %s"
            cursor.execute(query, (subject_name, subject_id))

        connection.commit()

        return {"success": True, "message": "科目更新成功"}

    except Error as e:
        return {"success": False, "error": f"更新科目失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def delete_subject(subject_id: int) -> Dict[str, Any]:
    """删除科目（级联删除相关题库）"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 检查科目是否存在
        cursor.execute("SELECT subject_id FROM subject WHERE subject_id = %s", (subject_id,))
        if not cursor.fetchone():
            return {"success": False, "error": "科目不存在"}

        # 获取相关题库文件路径（用于删除文件）
        cursor.execute("SELECT tiku_position FROM tiku WHERE subject_id = %s", (subject_id,))
        file_paths = [row[0] for row in cursor.fetchall()]

        # 开始事务
        connection.start_transaction()

        # 删除相关题库记录
        cursor.execute("DELETE FROM tiku WHERE subject_id = %s", (subject_id,))

        # 删除科目
        cursor.execute("DELETE FROM subject WHERE subject_id = %s", (subject_id,))

        connection.commit()

        return {
            "success": True,
            "message": "科目删除成功",
            "deleted_files": file_paths
        }

    except Error as e:
        connection.rollback()
        return {"success": False, "error": f"删除科目失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def get_tiku_by_subject(subject_id: int = None) -> list:
    """获取题库列表"""
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()

        if subject_id:
            query = """
                    SELECT t.tiku_id,
                           t.subject_id,
                           s.subject_name,
                           t.tiku_name,
                           t.tiku_position,
                           t.tiku_nums,
                           t.file_size,
                           t.file_hash,
                           t.is_active,
                           t.created_at,
                           t.updated_at
                    FROM tiku t
                             JOIN subject s ON t.subject_id = s.subject_id
                    WHERE t.subject_id = %s
                    ORDER BY t.tiku_name \
                    """
            cursor.execute(query, (subject_id,))
        else:
            query = """
                    SELECT t.tiku_id,
                           t.subject_id,
                           s.subject_name,
                           t.tiku_name,
                           t.tiku_position,
                           t.tiku_nums,
                           t.file_size,
                           t.file_hash,
                           t.is_active,
                           t.created_at,
                           t.updated_at
                    FROM tiku t
                             JOIN subject s ON t.subject_id = s.subject_id
                    ORDER BY s.subject_name, t.tiku_name \
                    """
            cursor.execute(query)

        tiku_list = []
        for row in cursor.fetchall():
            tiku_list.append({
                'tiku_id': row[0],
                'subject_id': row[1],
                'subject_name': row[2],
                'tiku_name': row[3],
                'tiku_position': row[4],
                'tiku_nums': row[5],
                'file_size': row[6],
                'file_hash': row[7],
                'is_active': bool(row[8]),
                'created_at': row[9].isoformat() if row[9] else None,
                'updated_at': row[10].isoformat() if row[10] else None
            })
        return tiku_list

    except Error as e:
        print(f"Error getting tiku: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def create_or_update_tiku(subject_id: int, tiku_name: str, tiku_position: str,
                          tiku_nums: int, file_size: int = 0, file_hash: str = None) -> Dict[str, Any]:
    """创建或更新题库信息"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 检查科目是否存在
        cursor.execute("SELECT subject_id FROM subject WHERE subject_id = %s", (subject_id,))
        if not cursor.fetchone():
            return {"success": False, "error": "科目不存在"}

        # 检查是否已存在相同路径的题库
        cursor.execute("SELECT tiku_id FROM tiku WHERE tiku_position = %s", (tiku_position,))
        existing_tiku = cursor.fetchone()

        if existing_tiku:
            # 更新现有题库
            query = """
                    UPDATE tiku
                    SET subject_id = %s,
                        tiku_name  = %s,
                        tiku_nums  = %s,
                        file_size  = %s,
                        file_hash  = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tiku_position = %s \
                    """
            cursor.execute(query, (subject_id, tiku_name, tiku_nums, file_size, file_hash, tiku_position))
            tiku_id = existing_tiku[0]
            action = "更新"
        else:
            # 创建新题库
            query = """
                    INSERT INTO tiku (subject_id, tiku_name, tiku_position, tiku_nums, file_size, file_hash)
                    VALUES (%s, %s, %s, %s, %s, %s) \
                    """
            cursor.execute(query, (subject_id, tiku_name, tiku_position, tiku_nums, file_size, file_hash))
            tiku_id = cursor.lastrowid
            action = "创建"

        connection.commit()

        return {
            "success": True,
            "tiku_id": tiku_id,
            "message": f"题库{action}成功"
        }

    except Error as e:
        return {"success": False, "error": f"{action}题库失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def delete_tiku(tiku_id: int) -> Dict[str, Any]:
    """删除题库"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 获取题库信息
        cursor.execute("SELECT tiku_position FROM tiku WHERE tiku_id = %s", (tiku_id,))
        result = cursor.fetchone()
        if not result:
            return {"success": False, "error": "题库不存在"}

        file_path = result[0]

        # 删除题库记录
        cursor.execute("DELETE FROM tiku WHERE tiku_id = %s", (tiku_id,))
        connection.commit()

        return {
            "success": True,
            "message": "题库删除成功",
            "file_path": file_path
        }

    except Error as e:
        return {"success": False, "error": f"删除题库失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def toggle_tiku_status(tiku_id: int) -> Dict[str, Any]:
    """切换题库启用状态"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()

        # 获取当前状态
        cursor.execute("SELECT is_active FROM tiku WHERE tiku_id = %s", (tiku_id,))
        result = cursor.fetchone()
        if not result:
            return {"success": False, "error": "题库不存在"}

        current_status = bool(result[0])
        new_status = not current_status

        # 更新状态
        cursor.execute("UPDATE tiku SET is_active = %s WHERE tiku_id = %s", (new_status, tiku_id))
        connection.commit()

        return {
            "success": True,
            "is_active": new_status,
            "message": f"题库已{'启用' if new_status else '禁用'}"
        }

    except Error as e:
        return {"success": False, "error": f"更新题库状态失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def batch_update_tiku_usage(usage_stats: dict) -> dict[str, bool | str] | dict[str, bool | int | str | Any] | None:
    """批量更新题库使用次数"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    all_counts = 0
    try:
        # 确保事务管理正确
        connection.autocommit = False
        cursor = connection.cursor()

        # 开始事务
        connection.start_transaction()

        updated_count = 0
        updated_subjects = set()

        for tiku_id, usage_count in usage_stats.items():
            # 更新题库使用次数
            update_tiku_query = """
                                UPDATE tiku
                                SET used_count = used_count + %s
                                WHERE tiku_id = %s
                                """
            cursor.execute(update_tiku_query, (usage_count, tiku_id))
            all_counts += usage_count

            if cursor.rowcount > 0:
                updated_count += 1

                # 获取对应的科目ID并更新科目使用次数
                cursor.execute("SELECT subject_id FROM tiku WHERE tiku_id = %s", (tiku_id,))
                result = cursor.fetchone()
                if result:
                    subject_id = result[0]
                    updated_subjects.add(subject_id)

        # 更新科目使用次数
        for subject_id in updated_subjects:
            update_subject_query = """
                                   UPDATE subject
                                   SET used_count = (SELECT COALESCE(SUM(used_count), 0)
                                                     FROM tiku
                                                     WHERE subject_id = %s)
                                   WHERE subject_id = %s
                                   """
            cursor.execute(update_subject_query, (subject_id, subject_id))

        connection.commit()

        return {
            "success": True,
            "updated_tiku_count": updated_count,
            "updated_subject_count": len(updated_subjects),
            "message": f"成功更新{updated_count}个题库和{len(updated_subjects)}个科目的使用次数{all_counts}次"
        }

    except Error as e:
        try:
            if connection:
                connection.rollback()
        except:
            pass
        return {"success": False, "error": f"批量更新使用次数失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.autocommit = True  # 恢复默认设置
                connection.close()
        except:
            pass  # 忽略清理时的错误


def get_usage_statistics() -> dict[str, bool | str] | dict[str, bool | list[dict[str, Any]] | list[Any]] | None:
    """获取使用统计信息"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        cursor = connection.cursor()

        # 获取科目使用统计
        cursor.execute("""
                       SELECT subject_name, used_count
                       FROM subject
                       ORDER BY used_count DESC
                       LIMIT 10
                       """)
        subject_stats = [{"subject_name": row[0], "used_count": row[1]} for row in cursor.fetchall()]

        # 获取题库使用统计（前20）
        cursor.execute("""
                       SELECT t.tiku_name, s.subject_name, t.used_count, t.tiku_position
                       FROM tiku t
                                JOIN subject s ON t.subject_id = s.subject_id
                       ORDER BY t.used_count DESC
                       LIMIT 20
                       """)
        tiku_stats = []
        for row in cursor.fetchall():
            tiku_stats.append({
                "tiku_name": row[0],
                "subject_name": row[1],
                "used_count": row[2],
                "tiku_position": row[3]
            })

        return {
            "success": True,
            "subject_stats": subject_stats,
            "tiku_stats": tiku_stats
        }

    except Error as e:
        return {"success": False, "error": f"获取使用统计失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            return None


# 题目管理相关函数
def insert_questions_batch(questions_data: list) -> Dict[str, Any]:
    """批量插入题目到数据库"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        connection.autocommit = False
        cursor = connection.cursor()

        # 开始事务
        connection.start_transaction()

        insert_query = """
                       INSERT INTO questions (subject_id, tiku_id, question_type, stem, option_a, option_b, option_c,
                                              option_d, answer, explanation, difficulty, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) \
                       """

        inserted_count = 0
        for question in questions_data:
            cursor.execute(insert_query, (
                question['subject_id'],
                question['tiku_id'],
                question['question_type'],
                question['stem'],
                question.get('option_a'),
                question.get('option_b'),
                question.get('option_c'),
                question.get('option_d'),
                question['answer'],
                question.get('explanation'),
                question.get('difficulty', 1),
                question.get('status', 'active')
            ))
            inserted_count += 1

        connection.commit()

        return {
            "success": True,
            "inserted_count": inserted_count,
            "message": f"成功插入{inserted_count}道题目"
        }

    except Error as e:
        try:
            if connection:
                connection.rollback()
        except:
            pass
        return {"success": False, "error": f"批量插入题目失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.autocommit = True
                connection.close()
        except:
            pass


def get_questions_by_tiku(tiku_id: int = None) -> list:
    """根据题库ID获取题目列表，如果不指定则获取所有题目"""
    connection = get_db_connection()
    if not connection:
        return []

    cursor = None
    try:
        cursor = connection.cursor()

        if tiku_id:
            query = """
                    SELECT q.id,
                           q.subject_id,
                           q.tiku_id,
                           q.question_type,
                           q.stem,
                           q.option_a,
                           q.option_b,
                           q.option_c,
                           q.option_d,
                           q.answer,
                           q.explanation,
                           q.difficulty,
                           q.status,
                           s.subject_name,
                           t.tiku_name
                    FROM questions q
                             LEFT JOIN subject s ON q.subject_id = s.subject_id
                             LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
                    WHERE q.tiku_id = %s
                      AND q.status = 'active'
                    ORDER BY q.id \
                    """
            cursor.execute(query, (tiku_id,))
        else:
            query = """
                    SELECT q.id,
                           q.subject_id,
                           q.tiku_id,
                           q.question_type,
                           q.stem,
                           q.option_a,
                           q.option_b,
                           q.option_c,
                           q.option_d,
                           q.answer,
                           q.explanation,
                           q.difficulty,
                           q.status,
                           s.subject_name,
                           t.tiku_name
                    FROM questions q
                             LEFT JOIN subject s ON q.subject_id = s.subject_id
                             LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
                    WHERE q.status = 'active'
                    ORDER BY q.tiku_id, q.id \
                    """
            cursor.execute(query)

        questions = []
        for row in cursor.fetchall():
            question_id, subject_id, tiku_id, question_type, stem, option_a, option_b, option_c, option_d, answer, explanation, difficulty, status, subject_name, tiku_name = row

            # 构造选项字典
            options_for_practice = {}
            if option_a:
                options_for_practice['A'] = option_a
            if option_b:
                options_for_practice['B'] = option_b
            if option_c:
                options_for_practice['C'] = option_c
            if option_d:
                options_for_practice['D'] = option_d

            # 处理题目类型
            if question_type == 0:
                type_name = '单选题'
                is_multiple_choice = False
            elif question_type == 5:
                type_name = '多选题'
                is_multiple_choice = True
            elif question_type == 10:
                type_name = '判断题'
                is_multiple_choice = False
                options_for_practice = None  # 判断题不需要选项
            else:
                type_name = '未知题型'
                is_multiple_choice = False

            questions.append({
                'id': question_id,
                'subject_id': subject_id,
                'tiku_id': tiku_id,
                'type': type_name,
                'question': stem,
                'options_for_practice': options_for_practice,
                'answer': answer,
                'is_multiple_choice': is_multiple_choice,
                'explanation': explanation,
                'difficulty': difficulty,
                'subject_name': subject_name,
                'tiku_name': tiku_name
            })

        return questions

    except Error as e:
        print(f"Error getting questions: {e}")
        return []
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def get_all_questions_by_tiku_dict() -> dict:
    """获取所有题目，按题库ID分组返回字典"""
    connection = get_db_connection()
    if not connection:
        return {}

    cursor = None
    try:
        cursor = connection.cursor()

        query = """
                SELECT q.id,
                       q.subject_id,
                       q.tiku_id,
                       q.question_type,
                       q.stem,
                       q.option_a,
                       q.option_b,
                       q.option_c,
                       q.option_d,
                       q.answer,
                       q.explanation,
                       q.difficulty,
                       q.status,
                       s.subject_name,
                       t.tiku_name,
                       t.tiku_position
                FROM questions q
                         LEFT JOIN subject s ON q.subject_id = s.subject_id
                         LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
                WHERE q.status = 'active'
                  AND t.is_active = 1
                ORDER BY q.tiku_id, q.id \
                """
        cursor.execute(query)

        questions_dict = {}
        for row in cursor.fetchall():
            question_id, subject_id, tiku_id, question_type, stem, option_a, option_b, option_c, option_d, answer, explanation, difficulty, status, subject_name, tiku_name, tiku_position = row

            # 构造选项字典
            options_for_practice = {}
            if option_a:
                options_for_practice['A'] = option_a
            if option_b:
                options_for_practice['B'] = option_b
            if option_c:
                options_for_practice['C'] = option_c
            if option_d:
                options_for_practice['D'] = option_d

            # 处理题目类型
            if question_type == 0:
                type_name = '单选题'
                is_multiple_choice = False
            elif question_type == 5:
                type_name = '多选题'
                is_multiple_choice = True
            elif question_type == 10:
                type_name = '判断题'
                is_multiple_choice = False
                options_for_practice = None  # 判断题不需要选项
            else:
                type_name = '未知题型'
                is_multiple_choice = False

            question_data = {
                'id': f"db_{question_id}",
                'db_id': question_id,
                'subject_id': subject_id,
                'tiku_id': tiku_id,
                'type': type_name,
                'question': stem,
                'options_for_practice': options_for_practice,
                'answer': answer,
                'is_multiple_choice': is_multiple_choice,
                'explanation': explanation,
                'difficulty': difficulty,
                'subject_name': subject_name,
                'tiku_name': tiku_name
            }

            # 使用tiku_position作为key以保持与现有代码的兼容性
            tiku_key = tiku_id
            if tiku_key not in questions_dict:
                questions_dict[tiku_key] = []
            questions_dict[tiku_key].append(question_data)

        return questions_dict

    except Error as e:
        print(f"Error getting all questions: {e}")
        return {}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def delete_questions_by_tiku(tiku_id: int) -> Dict[str, Any]:
    """删除指定题库的所有题目"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        cursor = connection.cursor()

        # 先获取要删除的题目数量
        cursor.execute("SELECT COUNT(*) FROM questions WHERE tiku_id = %s", (tiku_id,))
        count = cursor.fetchone()[0]

        # 删除题目
        cursor.execute("DELETE FROM questions WHERE tiku_id = %s", (tiku_id,))
        connection.commit()

        return {
            "success": True,
            "deleted_count": count,
            "message": f"成功删除{count}道题目"
        }

    except Error as e:
        return {"success": False, "error": f"删除题目失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def parse_excel_to_questions(subject_id: int, tiku_id: int, questions_data: list) -> list:
    """将Excel解析的数据转换为数据库格式"""
    db_questions = []

    for question in questions_data:
        # 解析题目类型
        if question['type'] == '单选题':
            question_type = 0
        elif question['type'] == '多选题':
            question_type = 5
        elif question['type'] == '判断题':
            question_type = 10
        else:
            continue  # 跳过未知类型

        # 处理选项
        options = question.get('options_for_practice', {})
        option_a = options.get('A') if options else None
        option_b = options.get('B') if options else None
        option_c = options.get('C') if options else None
        option_d = options.get('D') if options else None

        db_question = {
            'subject_id': subject_id,
            'tiku_id': tiku_id,
            'question_type': question_type,
            'stem': question['question'],
            'option_a': option_a,
            'option_b': option_b,
            'option_c': option_c,
            'option_d': option_d,
            'answer': question['answer'],
            'explanation': question.get('analysis', ''),
            'difficulty': 1,  # 默认难度
            'status': 'active'
        }

        db_questions.append(db_question)

    return db_questions


def toggle_user_status(user_id: int) -> Dict[str, Any]:
    """切换用户启用/禁用状态"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        cursor = connection.cursor()

        # 获取当前状态
        cursor.execute("SELECT is_enabled, username FROM user_accounts WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if not result:
            return {"success": False, "error": "用户不存在"}

        current_status, username = result
        new_status = not current_status

        # 更新状态
        cursor.execute("UPDATE user_accounts SET is_enabled = %s WHERE id = %s", (new_status, user_id))
        connection.commit()

        return {
            "success": True,
            "is_enabled": new_status,
            "username": username,
            "message": f"用户已{'启用' if new_status else '禁用'}"
        }

    except Error as e:
        return {"success": False, "error": f"切换用户状态失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def update_user_model(user_id: int, model: int) -> Dict[str, Any]:
    """更新用户权限模型"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        cursor = connection.cursor()

        # 检查用户是否存在并获取用户名
        cursor.execute("SELECT id, username FROM user_accounts WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            return {"success": False, "error": "用户不存在"}

        username = user_data[1]

        # 更新模型
        cursor.execute("UPDATE user_accounts SET model = %s WHERE id = %s", (model, user_id))
        connection.commit()

        model_names = {0: "普通用户", 5: "VIP用户", 10: "管理员"}
        return {
            "success": True,
            "user_id": user_id,
            "username": username,
            "model": model,
            "model_name": model_names.get(model, "未知"),
            "message": f"用户权限已更新为{model_names.get(model, '未知')}"
        }

    except Error as e:
        return {"success": False, "error": f"更新用户权限失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def delete_invitation_code(invitation_id: int) -> Dict[str, Any]:
    """删除未使用的邀请码"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        cursor = connection.cursor()

        # 检查邀请码是否存在并获取详细信息
        cursor.execute("""
                       SELECT id, code, is_used, used_by_user_id
                       FROM invitation_codes
                       WHERE id = %s
                       """, (invitation_id,))
        result = cursor.fetchone()

        if not result:
            return {"success": False, "error": "邀请码不存在"}

        inv_id, code, is_used, used_by_user_id = result

        # 检查邀请码是否已被使用
        if is_used or used_by_user_id:
            return {"success": False, "error": "不能删除已使用的邀请码"}

        # 删除邀请码
        cursor.execute("DELETE FROM invitation_codes WHERE id = %s", (invitation_id,))
        connection.commit()

        if cursor.rowcount == 0:
            return {"success": False, "error": "删除失败，邀请码可能已被删除"}

        return {
            "success": True,
            "message": f"邀请码 {code} 删除成功",
            "deleted_code": code
        }

    except Error as e:
        return {"success": False, "error": f"删除邀请码失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass


def create_practice_session(user_id: int, tiku_id: int, session_type: str = 'normal', 
                           shuffle_enabled: bool = True, selected_types: list = None,
                           total_questions: int = 0, question_indices: list = None) -> Dict[str, Any]:
    """创建新的练习会话记录"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()
        
        # 将列表转换为JSON字符串
        selected_types_json = json.dumps(selected_types, ensure_ascii=False) if selected_types else None
        question_indices_json = json.dumps(question_indices, ensure_ascii=False) if question_indices else None
        
        query = """
        INSERT INTO practice_sessions 
        (user_id, tiku_id, session_type, shuffle_enabled, selected_types, 
         total_questions, question_indices, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
        """
        
        cursor.execute(query, (
            user_id, tiku_id, session_type, shuffle_enabled, 
            selected_types_json, total_questions, question_indices_json
        ))
        
        connection.commit()
        session_id = cursor.lastrowid
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "练习会话创建成功"
        }
        
    except Error as e:
        return {"success": False, "error": f"创建练习会话失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def update_practice_session(session_id: int, **kwargs) -> Dict[str, Any]:
    """更新练习会话记录"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()
        
        # 构建动态更新语句
        update_fields = []
        values = []
        
        for field, value in kwargs.items():
            if field in ['current_question_index', 'correct_first_try', 'round_number', 'status']:
                update_fields.append(f"{field} = %s")
                values.append(value)
            elif field in ['question_indices', 'wrong_indices', 'question_statuses', 'answer_history']:
                update_fields.append(f"{field} = %s")
                values.append(json.dumps(value, ensure_ascii=False) if value is not None else None)
        
        if not update_fields:
            return {"success": False, "error": "没有有效的更新字段"}
        
        values.append(session_id)
        query = f"UPDATE practice_sessions SET {', '.join(update_fields)}, updated_at = NOW() WHERE id = %s"
        
        cursor.execute(query, values)
        connection.commit()
        
        return {
            "success": True,
            "updated_rows": cursor.rowcount,
            "message": "练习会话更新成功"
        }
        
    except Error as e:
        return {"success": False, "error": f"更新练习会话失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def complete_practice_session(session_id: int, final_stats: dict = None) -> Dict[str, Any]:
    """标记练习会话为完成状态"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    try:
        cursor = connection.cursor()
        
        query = """
        UPDATE practice_sessions 
        SET status = 'completed', completed_at = NOW(), updated_at = NOW()
        WHERE id = %s AND status = 'active'
        """
        
        cursor.execute(query, (session_id,))
        connection.commit()
        
        if cursor.rowcount > 0:
            # 如果提供了最终统计数据，更新统计表
            if final_stats:
                update_practice_statistics(session_id, final_stats)
            
            return {
                "success": True,
                "message": "练习会话已完成"
            }
        else:
            return {
                "success": False,
                "error": "会话不存在或已完成"
            }
        
    except Error as e:
        return {"success": False, "error": f"完成练习会话失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def get_practice_session(session_id: int) -> Optional[Dict[str, Any]]:
    """获取练习会话记录"""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        
        query = """
        SELECT id, user_id, tiku_id, session_type, shuffle_enabled, selected_types,
               total_questions, current_question_index, correct_first_try, round_number,
               status, question_indices, wrong_indices, question_statuses, answer_history,
               created_at, updated_at, completed_at
        FROM practice_sessions 
        WHERE id = %s
        """
        
        cursor.execute(query, (session_id,))
        result = cursor.fetchone()
        
        if result:
            # 解析JSON字段
            return {
                'id': result[0],
                'user_id': result[1],
                'tiku_id': result[2],
                'session_type': result[3],
                'shuffle_enabled': result[4],
                'selected_types': json.loads(result[5]) if result[5] else None,
                'total_questions': result[6],
                'current_question_index': result[7],
                'correct_first_try': result[8],
                'round_number': result[9],
                'status': result[10],
                'question_indices': json.loads(result[11]) if result[11] else None,
                'wrong_indices': json.loads(result[12]) if result[12] else None,
                'question_statuses': json.loads(result[13]) if result[13] else None,
                'answer_history': json.loads(result[14]) if result[14] else None,
                'created_at': result[15],
                'updated_at': result[16],
                'completed_at': result[17]
            }
        
        return None
        
    except Error as e:
        print(f"获取练习会话失败: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

@with_db_connection
def get_user_active_practice_session(cursor, user_id: int, tiku_id: int = None) -> Optional[Dict[str, Any]]:
    """获取用户当前活跃的练习会话 - 优化版本"""
    logger.debug(f"查询用户 {user_id} 的活跃练习会话，tiku_id={tiku_id}")
    
    try:
        if tiku_id:
            # 查找特定题库的活跃会话，直接获取完整信息
            query = """
            SELECT id, user_id, tiku_id, session_type, shuffle_enabled, selected_types,
                   total_questions, current_question_index, correct_first_try, round_number,
                   status, question_indices, wrong_indices, question_statuses, answer_history,
                   created_at, updated_at, completed_at
            FROM practice_sessions 
            WHERE user_id = %s AND tiku_id = %s AND status = 'active'
            ORDER BY updated_at DESC LIMIT 1
            """
            cursor.execute(query, (user_id, tiku_id))
        else:
            # 查找任意活跃会话，直接获取完整信息
            query = """
            SELECT id, user_id, tiku_id, session_type, shuffle_enabled, selected_types,
                   total_questions, current_question_index, correct_first_try, round_number,
                   status, question_indices, wrong_indices, question_statuses, answer_history,
                   created_at, updated_at, completed_at
            FROM practice_sessions 
            WHERE user_id = %s AND status = 'active'
            ORDER BY updated_at DESC LIMIT 1
            """
            cursor.execute(query, (user_id,))
        
        result = cursor.fetchone()
        logger.debug(f"数据库查询结果: {result is not None}")
        
        if result:
            # 使用字典访问方式，因为 with_db_connection 装饰器设置了 dictionary=True
            session_data = {
                'id': result['id'],
                'user_id': result['user_id'],
                'tiku_id': result['tiku_id'],
                'session_type': result['session_type'],
                'shuffle_enabled': result['shuffle_enabled'],
                'selected_types': json.loads(result['selected_types']) if result['selected_types'] else None,
                'total_questions': result['total_questions'],
                'current_question_index': result['current_question_index'],
                'correct_first_try': result['correct_first_try'],
                'round_number': result['round_number'],
                'status': result['status'],
                'question_indices': json.loads(result['question_indices']) if result['question_indices'] else None,
                'wrong_indices': json.loads(result['wrong_indices']) if result['wrong_indices'] else None,
                'question_statuses': json.loads(result['question_statuses']) if result['question_statuses'] else None,
                'answer_history': json.loads(result['answer_history']) if result['answer_history'] else None,
                'created_at': result['created_at'],
                'updated_at': result['updated_at'],
                'completed_at': result['completed_at']
            }
            
            logger.debug(f"找到活跃会话: session_id={session_data['id']}, tiku_id={session_data['tiku_id']}")
            return session_data
        else:
            logger.debug(f"用户 {user_id} 没有活跃的练习会话")
        
        return None
        
    except Error as e:
        logger.error(f"获取用户活跃练习会话失败: {e}")
        import traceback
        logger.error(f"数据库查询异常详情: {traceback.format_exc()}")
        return None


def update_practice_statistics(session_id: int, stats: dict) -> bool:
    """更新练习统计数据"""
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        
        # 首先获取会话信息
        cursor.execute("SELECT user_id, tiku_id, created_at FROM practice_sessions WHERE id = %s", (session_id,))
        session_info = cursor.fetchone()
        
        if not session_info:
            return False
            
        user_id, tiku_id, created_at = session_info
        practice_date = created_at.date()
        
        # 插入或更新统计数据
        query = """
        INSERT INTO practice_statistics 
        (user_id, tiku_id, date, sessions_count, total_questions, correct_answers, practice_time_minutes)
        VALUES (%s, %s, %s, 1, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        sessions_count = sessions_count + 1,
        total_questions = total_questions + VALUES(total_questions),
        correct_answers = correct_answers + VALUES(correct_answers),
        practice_time_minutes = practice_time_minutes + VALUES(practice_time_minutes)
        """
        
        cursor.execute(query, (
            user_id, tiku_id, practice_date,
            stats.get('total_questions', 0),
            stats.get('correct_answers', 0),
            stats.get('practice_time_minutes', 0)
        ))
        
        connection.commit()
        return True
        
    except Error as e:
        print(f"更新练习统计失败: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


def get_user_practice_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """获取用户的练习历史记录"""
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        
        query = """
        SELECT ps.id, ps.tiku_id, t.tiku_name, s.subject_name, 
               ps.total_questions, ps.correct_first_try, ps.round_number,
               ps.status, ps.created_at, ps.completed_at
        FROM practice_sessions ps
        LEFT JOIN tiku t ON ps.tiku_id = t.tiku_id
        LEFT JOIN subject s ON t.subject_id = s.subject_id
        WHERE ps.user_id = %s 
        ORDER BY ps.created_at DESC 
        LIMIT %s
        """
        
        cursor.execute(query, (user_id, limit))
        results = cursor.fetchall()
        
        history = []
        for result in results:
            session_data = {
                'session_id': result[0],
                'tiku_id': result[1],
                'tiku_name': result[2] or 'Unknown',
                'subject_name': result[3] or 'Unknown',
                'total_questions': result[4],
                'correct_first_try': result[5],
                'round_number': result[6],
                'status': result[7],
                'created_at': result[8],
                'completed_at': result[9],
                'score_percent': (result[5] / result[4] * 100) if result[4] > 0 else 0
            }
            history.append(session_data)
        
        return history
        
    except Error as e:
        print(f"获取用户练习历史失败: {e}")
        return []
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()


@with_db_connection
def get_system_stats(cursor) -> Dict[str, Any]:
    """获取系统统计信息，供管理员使用"""
    stats = {}

    # 用户统计
    cursor.execute("SELECT COUNT(*) as total FROM user_accounts")
    stats['total_users'] = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as active FROM user_accounts WHERE is_enabled = TRUE")
    stats['active_users'] = cursor.fetchone()['active']

    cursor.execute("SELECT COUNT(*) as admins FROM user_accounts WHERE model = 10")
    stats['admin_users'] = cursor.fetchone()['admins']

    cursor.execute("SELECT COUNT(*) as vips FROM user_accounts WHERE model = 5")
    stats['vip_users'] = cursor.fetchone()['vips']

    # 邀请码统计
    cursor.execute("SELECT COUNT(*) as total FROM invitation_codes")
    stats['total_invitations'] = cursor.fetchone()['total']

    cursor.execute(
        "SELECT COUNT(*) as unused FROM invitation_codes WHERE is_used = FALSE AND (expires_at IS NULL OR expires_at > NOW())")
    stats['unused_invitations'] = cursor.fetchone()['unused']

    cursor.execute("SELECT COUNT(*) as used FROM invitation_codes WHERE is_used = TRUE")
    stats['used_invitations'] = cursor.fetchone()['used']

    # 题库统计 (Adjusted to match original admin panel fields more closely)
    cursor.execute("SELECT COUNT(*) as total_questions FROM questions WHERE status = 'active'") # Assuming 'active' status for questions
    stats['total_questions'] = cursor.fetchone()['total_questions']

    cursor.execute("SELECT COUNT(*) as total_files FROM tiku WHERE is_active = 1")
    stats['total_files'] = cursor.fetchone()['total_files']
    
    # Formatting to match the original structure expected by api_admin_get_stats
    formatted_stats = {
        'users': {
            'total': stats['total_users'],
            'active': stats['active_users'],
            'admins': stats['admin_users'],
            'vips': stats['vip_users']
        },
        'invitations': {
            'total': stats['total_invitations'],
            'unused': stats['unused_invitations'],
            'used': stats['used_invitations']
        },
        'subjects': { # Original key was 'subjects', though queries are for questions and files
            'total_questions': stats['total_questions'],
            'total_files': stats['total_files']
        }
    }
    return formatted_stats


@with_db_connection
def get_users_paginated(cursor, search: str, order_by: str, order_dir: str, page: int, per_page: int) -> Dict[str, Any]:
    """获取用户列表（分页和搜索）"""
    # 验证排序字段
    valid_order_fields = ['id', 'username', 'created_at', 'last_time_login', 'model']
    if order_by not in valid_order_fields:
        order_by = 'id'

    # 验证排序方向
    if order_dir.lower() not in ['asc', 'desc']:
        order_dir = 'desc'

    # 构建查询条件
    where_conditions = []
    query_params = []

    if search:
        where_conditions.append("u.username LIKE %s")
        query_params.append(f"%{search}%")

    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

    # 计算总数
    count_query = f"""
    SELECT COUNT(*) as total
    FROM user_accounts u
    {where_clause}
    """
    cursor.execute(count_query, query_params)
    total_count = cursor.fetchone()['total']

    # 计算分页信息
    total_pages = (total_count + per_page - 1) // per_page
    offset = (page - 1) * per_page

    # 获取用户列表
    query = f"""
    SELECT 
        u.id, u.username, u.is_enabled, u.created_at, u.last_time_login, u.model,
        i.code as invitation_code
    FROM user_accounts u
    LEFT JOIN invitation_codes i ON u.used_invitation_code_id = i.id
    {where_clause}
    ORDER BY u.{order_by} {order_dir.upper()}
    LIMIT %s OFFSET %s
    """
    cursor.execute(query, query_params + [per_page, offset])
    users_data = cursor.fetchall()

    users = []
    for user_row in users_data: # Changed variable name from user_data to user_row to avoid conflict
        users.append({
            'id': user_row['id'],
            'username': user_row['username'],
            'is_enabled': bool(user_row['is_enabled']),
            'created_at': user_row['created_at'].isoformat() if user_row['created_at'] else None,
            'last_time_login': user_row['last_time_login'].isoformat() if user_row['last_time_login'] else None,
            'model': user_row['model'] if user_row['model'] is not None else 0,
            'invitation_code': user_row['invitation_code']
        })

    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total_count,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }
    return {
        'users': users,
        'pagination': pagination
    }


@with_db_connection
def get_all_invitations_detailed(cursor) -> List[Dict[str, Any]]:
    """获取所有邀请码的详细列表"""
    query = """
            SELECT i.id,
                   i.code,
                   i.is_used,
                   i.created_at,
                   i.expires_at,
                   i.used_time,
                   u.username as used_by_username
            FROM invitation_codes i
                     LEFT JOIN user_accounts u ON i.used_by_user_id = u.id
            ORDER BY i.created_at DESC
            """
    cursor.execute(query)
    invitations_data = cursor.fetchall()

    invitations = []
    for inv_row in invitations_data:
        invitations.append({
            'id': inv_row['id'],
            'code': inv_row['code'],
            'is_used': bool(inv_row['is_used']),
            'created_at': inv_row['created_at'].isoformat() if inv_row['created_at'] else None,
            'expires_at': inv_row['expires_at'].isoformat() if inv_row['expires_at'] else None,
            'used_time': inv_row['used_time'].isoformat() if inv_row['used_time'] else None,
            'used_by_username': inv_row['used_by_username']
        })
    return invitations


@with_db_connection
def get_detailed_question_stats(cursor) -> Dict[str, Any]:
    """获取详细的题目统计信息"""
    stats = {}

    # 题目总数统计
    cursor.execute("SELECT COUNT(*) as total_questions FROM questions WHERE status = 'active'")
    stats['total_questions'] = cursor.fetchone()['total_questions']

    # 按题型统计
    cursor.execute("""
                   SELECT question_type, COUNT(*) as count
                   FROM questions
                   WHERE status = 'active'
                   GROUP BY question_type
                   """)
    type_stats_raw = cursor.fetchall()
    type_stats = []
    type_names = {0: '单选题', 5: '多选题', 10: '判断题'}
    for row in type_stats_raw:
        type_stats.append({
            'type': type_names.get(row['question_type'], f'类型{row["question_type"]}'),
            'type_code': row['question_type'],
            'count': row['count']
        })
    stats['type_stats'] = type_stats

    # 按科目统计
    cursor.execute("""
                   SELECT s.subject_name, COUNT(q.id) as count
                   FROM subject s
                            LEFT JOIN questions q
                                      ON s.subject_id = q.subject_id AND q.status = 'active'
                   GROUP BY s.subject_id, s.subject_name
                   ORDER BY count DESC
                   """)
    subject_stats_raw = cursor.fetchall()
    subject_stats = []
    for row in subject_stats_raw:
        subject_stats.append({
            'subject_name': row['subject_name'],
            'count': row['count']
        })
    stats['subject_stats'] = subject_stats

    # 按题库统计
    cursor.execute("""
                   SELECT t.tiku_name, s.subject_name, COUNT(q.id) as count
                   FROM tiku t
                            LEFT JOIN questions q
                                      ON t.tiku_id = q.tiku_id AND q.status = 'active'
                            LEFT JOIN subject s ON t.subject_id = s.subject_id
                   WHERE t.is_active = 1
                   GROUP BY t.tiku_id, t.tiku_name, s.subject_name
                   ORDER BY count DESC
                   """)
    tiku_stats_raw = cursor.fetchall()
    tiku_stats = []
    for row in tiku_stats_raw:
        tiku_stats.append({
            'tiku_name': row['tiku_name'],
            'subject_name': row['subject_name'],
            'count': row['count']
        })
    stats['tiku_stats'] = tiku_stats
    
    return stats


@with_db_connection
def get_question_details_by_id(cursor, question_id: int) -> Optional[Dict[str, Any]]:
    """获取单个题目详情"""
    query = """
            SELECT q.id,
                   q.subject_id,
                   q.tiku_id,
                   q.question_type,
                   q.stem,
                   q.option_a,
                   q.option_b,
                   q.option_c,
                   q.option_d,
                   q.answer,
                   q.explanation,
                   q.difficulty,
                   q.status,
                   q.created_at,
                   q.updated_at,
                   s.subject_name,
                   t.tiku_name
            FROM questions q
                     LEFT JOIN subject s ON q.subject_id = s.subject_id
                     LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
            WHERE q.id = %s
            """
    cursor.execute(query, (question_id,))
    row = cursor.fetchone()

    if not row:
        return None

    # cursor returns a dictionary when dictionary=True is set
    question_data = dict(row) # Ensure it's a mutable dict if further modifications are needed
    if question_data.get('created_at'):
        question_data['created_at'] = question_data['created_at'].isoformat()
    if question_data.get('updated_at'):
        question_data['updated_at'] = question_data['updated_at'].isoformat()

    return question_data


def create_question_and_update_tiku_count(question_data: Dict[str, Any]) -> Dict[str, Any]:
    """新增题目并更新题库题目数量（事务安全）"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False # Start transaction
        cursor = conn.cursor(dictionary=True)

        # 处理前端数据格式转换
        processed_data = question_data.copy()

        # 处理题目类型转换（从字符串转为数字）
        if 'question_type' in processed_data:
            type_str = processed_data['question_type']
            if type_str == '单选题':
                processed_data['question_type'] = 0
            elif type_str == '多选题':
                processed_data['question_type'] = 5
            elif type_str == '判断题':
                processed_data['question_type'] = 10
            else:
                conn.rollback()
                return {"success": False, "error": f"无效的题目类型: {type_str}"}

        # 处理选项数据转换（从options字典转为单独字段）
        if 'options' in processed_data and isinstance(processed_data['options'], dict):
            options = processed_data.pop('options')
            processed_data['option_a'] = options.get('A', '')
            processed_data['option_b'] = options.get('B', '')
            processed_data['option_c'] = options.get('C', '')
            processed_data['option_d'] = options.get('D', '')

        # 删除不需要的字段
        processed_data.pop('is_multiple_choice', None)  # 这个字段不存在于数据库中

        insert_query = """
                       INSERT INTO questions (subject_id, tiku_id, question_type, stem, option_a, option_b, option_c,
                                              option_d, answer, explanation, difficulty, status)
                       VALUES (%(subject_id)s, %(tiku_id)s, %(question_type)s, %(stem)s, 
                               %(option_a)s, %(option_b)s, %(option_c)s, %(option_d)s, 
                               %(answer)s, %(explanation)s, %(difficulty)s, %(status)s)
                       """
        
        # 确保必要字段存在并设置默认值
        params = {
            'subject_id': processed_data.get('subject_id'),
            'tiku_id': processed_data['tiku_id'],
            'question_type': processed_data['question_type'],
            'stem': processed_data['stem'],
            'option_a': processed_data.get('option_a', ''),
            'option_b': processed_data.get('option_b', ''),
            'option_c': processed_data.get('option_c', ''),
            'option_d': processed_data.get('option_d', ''),
            'answer': processed_data['answer'],
            'explanation': processed_data.get('explanation', ''),
            'difficulty': processed_data.get('difficulty', 1),
            'status': processed_data.get('status', 'active')
        }

        cursor.execute(insert_query, params)
        question_id = cursor.lastrowid

        # 更新题库的题目数量
        cursor.execute("SELECT COUNT(*) as count FROM questions WHERE tiku_id = %s AND status = 'active'", 
                       (processed_data['tiku_id'],))
        question_count = cursor.fetchone()['count']

        cursor.execute("UPDATE tiku SET tiku_nums = %s WHERE tiku_id = %s", 
                       (question_count, processed_data['tiku_id']))
        
        conn.commit()
        return {"success": True, "question_id": question_id, "message": "题目创建成功"}

    except Error as e:
        if conn:
            conn.rollback()
        logger.error(f"创建题目并更新题库数量失败: {e}") # Use existing logger if available, or define one
        return {"success": False, "error": f"创建题目失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.autocommit = True # Reset autocommit
            conn.close()


@with_db_connection
def update_question_details(cursor, question_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """更新题目详情"""
    try:
        # Check if question exists first
        cursor.execute("SELECT id, tiku_id FROM questions WHERE id = %s", (question_id,))
        question_info = cursor.fetchone()
        if not question_info:
            return {"success": False, "error": "题目不存在"}

        # 处理题目类型转换（从字符串转为数字）
        if 'question_type' in update_data:
            type_str = update_data['question_type']
            if type_str == '单选题':
                update_data['question_type'] = 0
            elif type_str == '多选题':
                update_data['question_type'] = 5
            elif type_str == '判断题':
                update_data['question_type'] = 10
            else:
                return {"success": False, "error": f"无效的题目类型: {type_str}"}

        # 处理选项数据转换（从options字典转为单独字段）
        if 'options' in update_data and isinstance(update_data['options'], dict):
            options = update_data.pop('options')
            update_data['option_a'] = options.get('A', '')
            update_data['option_b'] = options.get('B', '')
            update_data['option_c'] = options.get('C', '')
            update_data['option_d'] = options.get('D', '')

        # 删除不需要的字段
        update_data.pop('is_multiple_choice', None)  # 这个字段不存在于数据库中

        fields_mapping = {
            'subject_id': 'subject_id',
            'tiku_id': 'tiku_id',
            'question_type': 'question_type',
            'stem': 'stem',
            'option_a': 'option_a',
            'option_b': 'option_b',
            'option_c': 'option_c',
            'option_d': 'option_d',
            'answer': 'answer',
            'explanation': 'explanation',
            'difficulty': 'difficulty',
            'status': 'status'
        }

        set_clauses = []
        values = []

        for field_key, db_column_name in fields_mapping.items():
            if field_key in update_data:
                set_clauses.append(f"{db_column_name} = %s")
                values.append(update_data[field_key])
        
        if not set_clauses:
            return {"success": False, "error": "没有有效的更新字段"}

        values.append(question_id)
        update_query = f"UPDATE questions SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = %s"
        
        cursor.execute(update_query, values)
        
        if cursor.rowcount > 0:
            return {"success": True, "message": "题目更新成功"}
        else:
            return {"success": False, "error": "更新失败，没有影响任何记录"}

    except Exception as e:
        logger.error(f"更新题目详情失败: {e}")
        return {"success": False, "error": f"更新题目失败: {str(e)}"}


def delete_question_and_update_tiku_count(question_id: int) -> Dict[str, Any]:
    """删除题目并更新题库题目数量（事务安全）"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False # Start transaction
        cursor = conn.cursor(dictionary=True)

        # Check if question exists and get tiku_id
        cursor.execute("SELECT tiku_id FROM questions WHERE id = %s", (question_id,))
        question_info = cursor.fetchone()
        if not question_info:
            conn.rollback() # Nothing to do, rollback to be safe
            return {"success": False, "error": "题目不存在"} # Not found
        
        tiku_id = question_info['tiku_id']

        # Delete the question
        cursor.execute("DELETE FROM questions WHERE id = %s", (question_id,))
        deleted_rows = cursor.rowcount

        if deleted_rows == 0:
            conn.rollback() # Should not happen if found above, but good for safety
            return {"success": False, "error": "删除题目失败"}

        # Update tiku_nums for the tiku
        if tiku_id is not None: # Only update if tiku_id was associated
            cursor.execute("SELECT COUNT(*) as count FROM questions WHERE tiku_id = %s AND status = 'active'", (tiku_id,))
            question_count = cursor.fetchone()['count']
            cursor.execute("UPDATE tiku SET tiku_nums = %s WHERE tiku_id = %s", (question_count, tiku_id))
        
        conn.commit()
        return {"success": True, "message": "题目删除成功", "tiku_id_affected": tiku_id}

    except Error as e:
        if conn:
            conn.rollback()
        logger.error(f"删除题目并更新题库数量失败: {e}")
        return {"success": False, "error": f"删除题目操作失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.autocommit = True # Reset autocommit
            conn.close()


def toggle_question_status_and_update_tiku_count(question_id: int) -> Dict[str, Any]:
    """切换题目状态并更新题库题目数量（事务安全）"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        conn.autocommit = False # Start transaction
        cursor = conn.cursor(dictionary=True)

        # Get current status and tiku_id
        cursor.execute("SELECT status, tiku_id FROM questions WHERE id = %s", (question_id,))
        question_info = cursor.fetchone()
        if not question_info:
            conn.rollback()
            return {"success": False, "error": "题目不存在"}
        
        current_status = question_info['status']
        tiku_id = question_info['tiku_id']
        new_status = 'inactive' if current_status == 'active' else 'active'

        # Update question status
        cursor.execute("UPDATE questions SET status = %s, updated_at = NOW() WHERE id = %s", (new_status, question_id))
        updated_rows = cursor.rowcount

        if updated_rows == 0:
            conn.rollback() # Should not happen if found, but for safety
            return {"success": False, "error": "切换题目状态失败"}

        # Update tiku_nums for the tiku
        if tiku_id is not None:
            # Recalculate active questions for the tiku
            cursor.execute("SELECT COUNT(*) as count FROM questions WHERE tiku_id = %s AND status = 'active'", (tiku_id,))
            question_count = cursor.fetchone()['count']
            cursor.execute("UPDATE tiku SET tiku_nums = %s WHERE tiku_id = %s", (question_count, tiku_id))
        
        conn.commit()
        action_message = "启用" if new_status == 'active' else "禁用"
        return {"success": True, "message": f"题目{action_message}成功", "status": new_status, "tiku_id_affected": tiku_id}

    except Error as e:
        if conn:
            conn.rollback()
        logger.error(f"切换题目状态并更新题库数量失败: {e}")
        return {"success": False, "error": f"切换题目状态操作失败: {str(e)}"}
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.autocommit = True # Reset autocommit
            conn.close()


@with_db_connection
def get_questions_paginated(cursor, tiku_id: Optional[int], page: int, per_page: int) -> Dict[str, Any]:
    """获取题目列表（分页），可选按题库ID过滤"""
    base_query = """
                 FROM questions q
                 LEFT JOIN subject s ON q.subject_id = s.subject_id
                 LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
                 """
    count_query_base = "SELECT COUNT(q.id) as total " + base_query
    select_query_base = """SELECT q.id, q.subject_id, q.tiku_id, q.question_type, 
                                  q.stem, q.option_a, q.option_b, q.option_c, q.option_d, 
                                  q.answer, q.explanation, q.difficulty, q.status, 
                                  s.subject_name, t.tiku_name """ + base_query

    where_clauses = ["q.status = 'active'"]
    query_params = []

    if tiku_id is not None:
        where_clauses.append("q.tiku_id = %s")
        query_params.append(tiku_id)
    
    where_statement = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # Get total count
    cursor.execute(count_query_base + where_statement, query_params)
    total_count = cursor.fetchone()['total']

    # Paginate
    offset = (page - 1) * per_page
    order_clause = " ORDER BY q.tiku_id, q.id LIMIT %s OFFSET %s"
    
    final_query_params = query_params + [per_page, offset]
    cursor.execute(select_query_base + where_statement + order_clause, final_query_params)
    
    rows = cursor.fetchall()
    questions = []
    for row_dict in rows:
        # The format_question_for_display logic from get_questions_by_tiku can be reused or adapted here.
        # For now, returning the raw row_dict which is already a dictionary.
        # Datetime conversion to isoformat will be handled by the route if necessary.
        questions.append(row_dict)

    total_pages = (total_count + per_page - 1) // per_page
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_count,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages
    }

    return {
        'questions': questions,
        'pagination': pagination_info
    }

@with_db_connection
def get_question_by_db_id(cursor, question_db_id: int) -> Optional[Dict[str, Any]]:
    """根据数据库ID获取单个题目，并格式化以供练习使用"""
    query = """
            SELECT q.id, q.subject_id, q.tiku_id, q.question_type, q.stem,
                   q.option_a, q.option_b, q.option_c, q.option_d,
                   q.answer, q.explanation, q.difficulty, q.status,
                   s.subject_name, t.tiku_name
            FROM questions q
            LEFT JOIN subject s ON q.subject_id = s.subject_id
            LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
            WHERE q.id = %s AND q.status = 'active'
            """
    cursor.execute(query, (question_db_id,))
    row = cursor.fetchone()

    if not row:
        return None

    # Formatting logic adapted from the original get_questions_by_tiku
    question_id, subject_id, tiku_id, question_type_code, stem, option_a, option_b, option_c, option_d, answer, explanation, difficulty, status, subject_name, tiku_name = (
        row['id'], row['subject_id'], row['tiku_id'], row['question_type'], row['stem'], 
        row['option_a'], row['option_b'], row['option_c'], row['option_d'], 
        row['answer'], row['explanation'], row['difficulty'], row['status'], 
        row['subject_name'], row['tiku_name']
    )

    options_for_practice = {}
    if option_a: options_for_practice['A'] = option_a
    if option_b: options_for_practice['B'] = option_b
    if option_c: options_for_practice['C'] = option_c
    if option_d: options_for_practice['D'] = option_d

    type_name = '未知题型'
    is_multiple_choice = False
    if question_type_code == 0:  # 单选题
        type_name = '单选题'
    elif question_type_code == 5:  # 多选题
        type_name = '多选题'
        is_multiple_choice = True
    elif question_type_code == 10:  # 判断题
        type_name = '判断题'
        options_for_practice = None # Judgment questions don't need options

    return {
        'id': f"db_{question_id}", # Matches practice route id format
        'db_id': question_id,
        'subject_id': subject_id,
        'tiku_id': tiku_id,
        'type': type_name,
        'question': stem,
        'options_for_practice': options_for_practice,
        'answer': answer,
        'is_multiple_choice': is_multiple_choice,
        'explanation': explanation,
        'difficulty': difficulty,
        # 'status': status, # Status might not be needed directly in practice question object
        'subject_name': subject_name,
        'tiku_name': tiku_name
    }


@with_db_connection
def reset_user_password(cursor, user_id: int, new_password: str) -> Dict[str, Any]:
    """重置用户密码"""
    try:
        # 检查用户是否存在
        cursor.execute("SELECT id, username FROM user_accounts WHERE id = %s", (user_id,))
        user_record = cursor.fetchone()
        
        if not user_record:
            return {"success": False, "error": "用户不存在"}
        
        # 生成新密码哈希
        new_password_hash = hash_password(new_password)
        
        # 更新密码
        update_query = "UPDATE user_accounts SET password_hash = %s WHERE id = %s"
        cursor.execute(update_query, (new_password_hash, user_id))
        
        if cursor.rowcount == 0:
            return {"success": False, "error": "密码重置失败"}
        
        return {
            "success": True,
            "message": "密码重置成功",
            "user_id": user_id,
            "username": user_record['username']
        }
        
    except Error as e:
        return {"success": False, "error": f"重置密码失败: {str(e)}"}


if __name__ == "__main__":
    test_connection()
