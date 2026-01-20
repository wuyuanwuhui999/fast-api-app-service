import pymysql
import uuid

def update_user_ids_with_uuid():
    # 数据库连接配置（请按实际修改）
    config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'wwq_2021',
        'database': 'play',
        'charset': 'utf8mb4'
    }

    connection = pymysql.connect(**config)
    try:
        with connection.cursor() as cursor:
            # 1. 查询所有用户记录（获取主键或其他唯一标识）
            # 如果原表没有主键，建议先加一个自增临时主键（见下方说明）
            cursor.execute("SELECT id FROM user")
            rows = cursor.fetchall()

            # 开启事务
            connection.begin()

            for row in rows:
                old_id = row[0]
                new_id = uuid.uuid4().hex  # 32位小写UUID，如 'a1b2c3d4...'

                # 更新当前行
                cursor.execute(
                    "UPDATE user SET id = %s WHERE id = %s",
                    (new_id, old_id)
                )
                print(f"Updated: {old_id} -> {new_id}")

            # 提交事务
            connection.commit()
            print("✅ 所有用户 ID 已成功更新为唯一 32 位 UUID。")

    except Exception as e:
        connection.rollback()
        print(f"❌ 发生错误，已回滚: {e}")
    finally:
        connection.close()
update_user_ids_with_uuid()