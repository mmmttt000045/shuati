import mysql.connector
from mysql.connector import Error

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