import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from mysql.connector import Error
from mysql.connector import pooling

db_pool = None


def init_connection_pool():
    global db_pool
    try:
        db_pool = pooling.MySQLConnectionPool(
            pool_name="mypool",
            pool_size=1,  # 增加池大小以处理更多并发
            pool_reset_session=True,  # 确保每次获取的连接状态是干净的
            host="14.103.133.62",
            user="shuati",
            password="fxTWMaTLFyMMcKfh",
            database="shuati",
            port=3306,
            autocommit=True,  # 默认自动提交
            charset='utf8mb4',
            collation='utf8mb4_unicode_ci',
            connect_timeout=10,  # 连接超时
            sql_mode='STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'
        )
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
        return None
    try:
        # 从池中获取连接
        connection = db_pool.get_connection()
        return connection
    except Error as e:
        print(f"从连接池获取连接失败: {e}")
        return None


def hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_invitation_code(invitation_code: str) -> Optional[int]:
    """验证邀请码是否有效，返回邀请码ID"""
    connection = get_db_connection()
    if not connection:
        return None

    cursor = None
    try:
        cursor = connection.cursor()
        query = """
                SELECT id
                FROM invitation_codes
                WHERE code = %s
                  AND is_used = 0
                  AND (expires_at IS NULL OR expires_at > NOW())
                """
        cursor.execute(query, (invitation_code,))
        result = cursor.fetchone()
        return result[0] if result else None

    except Error as e:
        print(f"验证邀请码时发生错误: {e}")
        return None
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
        except:
            pass  # 忽略清理时的错误


def create_user(username: str, password: str, invitation_code_id: int) -> Dict[str, Any]:
    """创建新用户"""
    connection = get_db_connection()
    if not connection:
        return {"success": False, "error": "数据库连接失败"}

    cursor = None
    try:
        # 确保连接的autocommit设置正确
        connection.autocommit = False
        cursor = connection.cursor()

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
        affected_rows = cursor.execute(update_invitation_query, (user_id, invitation_code_id))

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
        except:
            pass  # 忽略回滚时的错误
        return {"success": False, "error": f"创建用户失败: {str(e)}"}
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.autocommit = True  # 恢复默认设置
                connection.close()
        except:
            pass  # 忽略清理时的错误


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
                WHERE username = %s \
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

        query = "UPDATE user_accounts SET last_time_login = NOW() WHERE id = %s;"
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
                WHERE id = %s \
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
                WHERE id = %s \
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


def save_user_session(user_id: int, session_data: Dict[str, Any]) -> bool:
    """保存用户的session数据到数据库"""
    connection = get_db_connection()
    if not connection:
        return False

    try:
        cursor = connection.cursor()
        session_json = json.dumps(session_data, ensure_ascii=False, default=str)

        query = """
                REPLACE
                INTO user_sessions (user_id, session_data, updated_at)
        VALUES (
                %s,
                %s,
                NOW
                (
                )
                ) \
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
                WHERE user_id = %s \
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
                DELETE
                FROM user_sessions
                WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR) \
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
                WHERE user_id = %s \
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

        for tiku_position, usage_count in usage_stats.items():
            # 更新题库使用次数
            update_tiku_query = """
                                UPDATE tiku
                                SET used_count = used_count + %s
                                WHERE tiku_position = %s
                                """
            cursor.execute(update_tiku_query, (usage_count, tiku_position))
            all_counts += usage_count

            if cursor.rowcount > 0:
                updated_count += 1

                # 获取对应的科目ID并更新科目使用次数
                cursor.execute("SELECT subject_id FROM tiku WHERE tiku_position = %s", (tiku_position,))
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
                       ORDER BY used_count DESC LIMIT 10
                       """)
        subject_stats = [{"subject_name": row[0], "used_count": row[1]} for row in cursor.fetchall()]

        # 获取题库使用统计（前20）
        cursor.execute("""
                       SELECT t.tiku_name, s.subject_name, t.used_count, t.tiku_position
                       FROM tiku t
                                JOIN subject s ON t.subject_id = s.subject_id
                       ORDER BY t.used_count DESC LIMIT 20
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
        INSERT INTO questions (subject_id, tiku_id, question_type, stem, option_a, option_b, option_c, option_d, answer, explanation, difficulty, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            SELECT q.id, q.subject_id, q.tiku_id, q.question_type, q.stem, 
                   q.option_a, q.option_b, q.option_c, q.option_d, q.answer, 
                   q.explanation, q.difficulty, q.status,
                   s.subject_name, t.tiku_name
            FROM questions q
            LEFT JOIN subject s ON q.subject_id = s.subject_id
            LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
            WHERE q.tiku_id = %s AND q.status = 'active'
            ORDER BY q.id
            """
            cursor.execute(query, (tiku_id,))
        else:
            query = """
            SELECT q.id, q.subject_id, q.tiku_id, q.question_type, q.stem, 
                   q.option_a, q.option_b, q.option_c, q.option_d, q.answer, 
                   q.explanation, q.difficulty, q.status,
                   s.subject_name, t.tiku_name
            FROM questions q
            LEFT JOIN subject s ON q.subject_id = s.subject_id
            LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
            WHERE q.status = 'active'
            ORDER BY q.tiku_id, q.id
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
        SELECT q.id, q.subject_id, q.tiku_id, q.question_type, q.stem, 
               q.option_a, q.option_b, q.option_c, q.option_d, q.answer, 
               q.explanation, q.difficulty, q.status,
               s.subject_name, t.tiku_name, t.tiku_position
        FROM questions q
        LEFT JOIN subject s ON q.subject_id = s.subject_id
        LEFT JOIN tiku t ON q.tiku_id = t.tiku_id
        WHERE q.status = 'active' AND t.is_active = 1
        ORDER BY q.tiku_id, q.id
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
            tiku_key = tiku_position if tiku_position else f"tiku_{tiku_id}"
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


if __name__ == "__main__":
    test_connection()
