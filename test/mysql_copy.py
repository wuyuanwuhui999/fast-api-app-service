import pymysql
import re
from pymysql import MySQLError

# ================== 配置区 ==================
SOURCE_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',        # ← 替换为实际远程用户
    'password': 'wwq_2021',
    'database': 'play',
    'charset': 'utf8mb4'
}

TARGET_CONFIG = {
    'host': '192.168.73.8',
    'port': 3306,
    'user': 'root',
    'password': 'wwq_2021',
    'database': 'play',
    'charset': 'utf8mb4'
}
# ==========================================

def ensure_dynamic_row_format(create_sql):
    """确保 CREATE TABLE 语句使用 ROW_FORMAT=DYNAMIC"""
    create_sql = re.sub(r'\s+ROW_FORMAT\s*=\s*\w+', '', create_sql, flags=re.IGNORECASE)
    create_sql = create_sql.rstrip().rstrip(';')
    return f"{create_sql} ROW_FORMAT=DYNAMIC;"

def get_create_table_statements(connection):
    """获取所有表的 CREATE TABLE 语句"""
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    create_statements = {}
    for table in tables:
        cursor.execute(f"SHOW CREATE TABLE `{table}`")
        result = cursor.fetchone()
        create_statements[table] = result[1]
    cursor.close()
    return create_statements

def get_table_data(connection, table_name):
    """获取指定表的所有数据"""
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(f"SELECT * FROM `{table_name}`")
    rows = cursor.fetchall()
    cursor.close()
    if not rows:
        return [], []
    columns = list(rows[0].keys())
    data = [tuple(row[col] for col in columns) for row in rows]
    return columns, data

def create_database_if_not_exists(host, port, user, password, db_name, charset='utf8mb4'):
    """在目标服务器创建数据库"""
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        charset=charset
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cursor.close()
    conn.close()

def main():
    print("🚀 开始复制数据库...")
    source_conn = None
    target_conn = None

    try:
        # === 1. 连接源数据库 ===
        print("🔌 连接源数据库...")
        source_conn = pymysql.connect(**SOURCE_CONFIG)

        # === 2. 获取建表语句 ===
        print("📋 获取建表语句...")
        create_statements = get_create_table_statements(source_conn)
        if not create_statements:
            print("⚠️ 源数据库中没有表，任务结束。")
            return

        # === 3. 创建目标数据库 ===
        print("🏗️ 创建目标数据库...")
        create_database_if_not_exists(
            TARGET_CONFIG['host'],
            TARGET_CONFIG['port'],
            TARGET_CONFIG['user'],
            TARGET_CONFIG['password'],
            TARGET_CONFIG['database'],
            TARGET_CONFIG['charset']
        )

        # === 4. 连接目标数据库，并显式启用 autocommit ===
        print("🔌 连接目标数据库（启用自动提交）...")
        target_conn = pymysql.connect(
            host=TARGET_CONFIG['host'],
            port=TARGET_CONFIG['port'],
            user=TARGET_CONFIG['user'],
            password=TARGET_CONFIG['password'],
            database=TARGET_CONFIG['database'],
            charset=TARGET_CONFIG['charset'],
            autocommit=True  # 👈 关键：确保插入立即生效
        )
        cursor = target_conn.cursor()

        # === 5. 关闭外键检查 ===
        print("🔒 临时关闭外键约束检查...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # === 6. 删除已有表 ===
        for table in create_statements:
            cursor.execute(f"DROP TABLE IF EXISTS `{table}`")

        # === 7. 创建新表 ===
        print("🔨 创建表结构（ROW_FORMAT=DYNAMIC）...")
        for table, create_sql in create_statements.items():
            safe_sql = ensure_dynamic_row_format(create_sql)
            cursor.execute(safe_sql)
            print(f"  ✅ 表 `{table}` 创建成功")

        # === 8. 插入数据（因 autocommit=True，无需 commit）===
        print("📥 导入数据...")
        for table in create_statements:
            print(f"  处理表: {table}")
            columns, data = get_table_data(source_conn, table)
            if not data:
                print(f"    ⚠️ 表 `{table}` 无数据")
                continue
            placeholders = ', '.join(['%s'] * len(columns))
            cols = ', '.join([f'`{col}`' for col in columns])
            insert_sql = f"INSERT INTO `{table}` ({cols}) VALUES ({placeholders})"
            cursor.executemany(insert_sql, data)
            print(f"    ✅ 成功插入 {len(data)} 行")

        # === 9. 重新启用外键检查 ===
        print("🔓 重新启用外键约束检查...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        print("\n✅ 数据库复制完成！所有表和数据均已同步。")

    except MySQLError as e:
        print(f"\n❌ MySQL 错误: {e}")
    except Exception as e:
        print(f"\n❌ 发生异常: {e}")
    finally:
        if source_conn:
            source_conn.close()
        if target_conn:
            target_conn.close()

if __name__ == '__main__':
    main()