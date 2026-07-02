import chromadb

# 1. 连接到 Chroma 服务
client = chromadb.HttpClient(host="localhost", port=8000)

# 2. 获取指定的集合
collection = client.get_collection(name="chat_vector_collection")


# 3. 封装查询函数
def query_collection(query_texts=None, n_results=5):
    """
    查询 Chroma 集合
    :param query_texts: 查询文本列表。如果为 None，则获取集合中的所有数据
    :param n_results: 语义查询时，每个查询返回的结果数量
    :return: 查询结果
    """
    if query_texts is None:
        # 获取所有数据（修复点：移除了 "distances"）
        print("提示：query_texts 为 None，正在获取集合中的所有数据...")
        results = collection.get(
            include=["documents", "metadatas"]
        )
        return results
    else:
        # 执行语义查询
        results = collection.query(
            query_texts=query_texts,
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )
        return results


# 4. 打印查询结果的辅助函数
def print_results(results, is_get_all=False):
    if results is None or not results['documents']:
        print("没有查询到任何数据。")
        return

    print("查询结果：")
    if is_get_all:
        # 处理 get() 返回的所有数据（一维列表）
        for i, doc in enumerate(results['documents']):
            print(f"{i + 1}. 文档内容: {doc}")
            print(f"   元数据: {results['metadatas'][i]}")
            print("-" * 40)
    else:
        # 处理 query() 返回的语义查询结果（二维列表）
        for i, docs in enumerate(results['documents']):
            print(f"\n[查询 {i + 1}]")
            for j, doc in enumerate(docs):
                print(f"  {j + 1}. 文档内容: {doc}")
                print(f"     距离: {results['distances'][i][j]:.4f}")
                print(f"     元数据: {results['metadatas'][i][j]}")
                print("-" * 40)


# 5. 使用示例
if __name__ == "__main__":
    # 场景1：传入 None，获取所有数据
    all_data = query_collection(None)
    print_results(all_data, is_get_all=True)

    # 场景2：正常传入文本进行语义查询
    search_res = query_collection(["准考证"])
    print_results(search_res, is_get_all=False)