import chromadb
import logging

# 配置日志，方便查看进度
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_and_delete_collection(source_collection_name: str,
                                  backup_collection_name: str,
                                  host: str = "localhost",
                                  port: int = 8000):
    """
    将源集合的数据完整复制到新集合中，复制成功后删除源集合。

    Args:
        source_collection_name (str): 源集合名称 (待删除).
        backup_collection_name (str): 备份集合名称 (新集合).
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

    try:
        # 2. 获取源集合
        src_collection = client.get_collection(name=source_collection_name)
        logger.info(f"找到源集合: {source_collection_name}, 包含 {src_collection.count()} 条数据")
    except Exception as e:
        logger.error(f"无法获取源集合 '{source_collection_name}': {e}")
        return False

    try:
        # 3. 创建/获取目标集合 (如果已存在，这里可能会报错，建议先处理或使用 get_or_create 逻辑)
        # 如果目标集合已存在，你可能需要先决定是覆盖还是报错。这里采用：如果存在则报错，防止误覆盖。
        try:
            dst_collection = client.create_collection(name=backup_collection_name)
            logger.info(f"已创建备份集合: {backup_collection_name}")
        except Exception as create_err:
            logger.warning(f"创建集合失败 (可能已存在): {create_err}")
            # 如果是已存在错误，尝试获取它
            dst_collection = client.get_collection(name=backup_collection_name)
            logger.info(f"使用已存在的集合: {backup_collection_name} 进行备份")

    except Exception as e:
        logger.error(f"无法创建或获取目标集合 '{backup_collection_name}': {e}")
        return False

    try:
        # 4. & 5. 读取所有数据并写入 (核心迁移逻辑)
        # get() 方法默认会返回所有数据
        data = src_collection.get(include=["embeddings", "metadatas", "documents"])

        # 检查是否有数据
        if not data['ids']:
            logger.warning("源集合中没有数据，直接删除。")
            client.delete_collection(name=source_collection_name)
            return True

        # 写入目标集合
        # 注意：ChromaDB 的 add 方法接受 lists
        dst_collection.add(
            ids=data['ids'],
            embeddings=data['embeddings'],
            metadatas=data['metadatas'],
            documents=data['documents']
        )

        logger.info(f"数据迁移成功！共迁移 {len(data['ids'])} 条记录。")

        # 6. 删除源集合
        client.delete_collection(name=source_collection_name)
        logger.info(f"源集合 '{source_collection_name}' 已删除。")

        print(f"✅ 操作完成：数据已从 '{source_collection_name}' 迁移到 '{backup_collection_name}' 并删除原集合。")
        return True

    except Exception as e:
        logger.error(f"数据迁移或删除过程中发生错误: {e}")
        return False


# --- 执行操作 ---
if __name__ == "__main__":
    # 定义集合名称
    SOURCE_COLLECTION = "chat_vector_collection"  # 原集合名
    BACKUP_COLLECTION = "chat_vector_collection_backup"  # 新集合名 (备份用)

    # 执行迁移删除
    migrate_and_delete_collection(SOURCE_COLLECTION, BACKUP_COLLECTION)