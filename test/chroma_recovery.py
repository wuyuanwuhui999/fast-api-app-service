import chromadb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def restore_collection(backup_collection_name: str,
                       target_collection_name: str,
                       overwrite_existing: bool = True,
                       host: str = "localhost",
                       port: int = 8000):
    """
    从备份集合恢复数据到目标集合。

    Args:
        backup_collection_name (str): 备份集合名称 (数据源).
        target_collection_name (str): 目标集合名称 (恢复到的位置).
        overwrite_existing (bool): 如果目标集合已存在，是否强制覆盖（清空后写入）。默认为 True。
        host (str): ChromaDB 服务地址.
        port (int): ChromaDB 端口.
    """

    # 1. 连接客户端
    try:
        client = chromadb.HttpClient(host=host, port=port)
        logger.info(f"成功连接到 ChromaDB 服务 {host}:{port}")
    except Exception as e:
        logger.error(f"连接服务失败: {e}")
        return False

    # 2. 检查备份集合是否存在
    try:
        backup_collection = client.get_collection(name=backup_collection_name)
        logger.info(f"找到备份集合: {backup_collection_name}, 包含 {backup_collection.count()} 条数据")
    except Exception as e:
        logger.error(f"无法获取备份集合 '{backup_collection_name}': {e}")
        return False

    # 3. 处理目标集合 (核心逻辑)
    try:
        if overwrite_existing:
            # 如果允许覆盖，先尝试删除已存在的目标集合，然后再创建新的
            try:
                client.delete_collection(name=target_collection_name)
                logger.info(f"目标集合 '{target_collection_name}' 已存在，已将其删除准备重建。")
            except ValueError:
                # ValueError 表示集合本来就不存在，这是正常的
                pass

        # 创建全新的目标集合
        target_collection = client.create_collection(name=target_collection_name)
        logger.info(f"已创建目标集合: {target_collection_name}")

    except Exception as e:
        logger.error(f"处理目标集合 '{target_collection_name}' 时发生错误: {e}")
        return False

    # 4. 读取备份数据并写入目标集合
    try:
        data = backup_collection.get(include=["embeddings", "metadatas", "documents"])

        if not data['ids']:
            logger.warning("备份集合中没有数据，无需恢复。")
            return True

        target_collection.add(
            ids=data['ids'],
            embeddings=data['embeddings'],
            metadatas=data['metadatas'],
            documents=data['documents']
        )

        logger.info(f"数据恢复成功！共恢复 {len(data['ids'])} 条记录到 '{target_collection_name}'。")
        print(f"✅ 恢复完成：数据已从 '{backup_collection_name}' 成功恢复到 '{target_collection_name}'。")
        return True

    except Exception as e:
        logger.error(f"数据恢复过程中发生错误: {e}")
        return False


# --- 执行操作 ---
if __name__ == "__main__":
    # 定义集合名称
    BACKUP_COLLECTION = "chat_vector_collection_backup"  # 备份集合名
    TARGET_COLLECTION = "chat_vector_collection"  # 要恢复到的目标集合名

    # 执行恢复 (如果目标集合已存在，会将其清空并重新写入备份数据)
    restore_collection(BACKUP_COLLECTION, TARGET_COLLECTION)