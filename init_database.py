#!/usr/bin/env python3
"""
数据库初始化脚本
用于创建user_sessions表以支持多端同步session功能
"""

from connectDB import get_db_connection
import mysql.connector
from mysql.connector import Error

def create_user_sessions_table():
    """创建用户session表"""
    connection = get_db_connection()
    if not connection:
        print("❌ 数据库连接失败")
        return False
    
    try:
        cursor = connection.cursor()
        
        # 创建user_sessions表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            session_data JSON NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_session (user_id),
            FOREIGN KEY (user_id) REFERENCES user_accounts(id) ON DELETE CASCADE,
            INDEX idx_updated_at (updated_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        
        cursor.execute(create_table_sql)
        print("✅ user_sessions表创建成功")
        
        # 创建清理过期session的存储过程
        # 首先检查存储过程是否已存在
        cursor.execute("SHOW PROCEDURE STATUS WHERE Name = 'CleanupExpiredSessions'")
        if not cursor.fetchone():
            create_procedure_sql = """
            CREATE PROCEDURE CleanupExpiredSessions()
            BEGIN
                DELETE FROM user_sessions 
                WHERE updated_at < DATE_SUB(NOW(), INTERVAL 2 HOUR);
                
                SELECT ROW_COUNT() as cleaned_sessions;
            END
            """
            cursor.execute(create_procedure_sql)
            print("✅ CleanupExpiredSessions存储过程创建成功")
        else:
            print("ℹ️  CleanupExpiredSessions存储过程已存在")
        
        connection.commit()
        return True
        
    except Error as e:
        print(f"❌ 创建表时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def check_database_status():
    """检查数据库状态"""
    connection = get_db_connection()
    if not connection:
        print("❌ 数据库连接失败")
        return False
    
    try:
        cursor = connection.cursor()
        
        # 检查user_accounts表是否存在
        cursor.execute("SHOW TABLES LIKE 'user_accounts'")
        if not cursor.fetchone():
            print("❌ user_accounts表不存在，请先创建基础用户表")
            return False
        
        # 检查user_sessions表是否存在
        cursor.execute("SHOW TABLES LIKE 'user_sessions'")
        if cursor.fetchone():
            print("✅ user_sessions表已存在")
            
            # 检查表结构
            cursor.execute("DESCRIBE user_sessions")
            columns = cursor.fetchall()
            print("📋 user_sessions表结构:")
            for column in columns:
                print(f"   - {column[0]}: {column[1]}")
        else:
            print("⚠️  user_sessions表不存在")
        
        return True
        
    except Error as e:
        print(f"❌ 检查数据库状态时出错: {e}")
        return False
    finally:
        if cursor:
            cursor.close()
        if connection.is_connected():
            connection.close()

def main():
    """主函数"""
    print("=== 数据库初始化脚本 ===")
    print("这个脚本将创建user_sessions表以支持多端同步session功能\n")
    
    # 检查数据库状态
    print("1. 检查数据库状态...")
    if not check_database_status():
        return
    
    # 创建user_sessions表
    print("\n2. 创建user_sessions表...")
    if create_user_sessions_table():
        print("\n✅ 数据库初始化完成！")
        print("现在您可以启动应用程序，享受多端同步的刷题体验。")
    else:
        print("\n❌ 数据库初始化失败，请检查错误信息。")

if __name__ == "__main__":
    main() 