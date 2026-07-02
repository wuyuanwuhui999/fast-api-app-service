import chromadb

# 1. 连接到本地运行的 Chroma 服务
client = chromadb.HttpClient(host="localhost", port=8000)

# 2. 指定要查询的集合名称
collection_name = "chat_vector_collection"

try:
    # 3. 获取集合对象
    # 如果集合不存在，get_collection 会抛出异常
    collection = client.get_collection(name=collection_name)

    # 4. 查询集合中的数据
    # 这里使用 get() 方法获取所有文档，limit 设置为 10 作为示例
    results = collection.get(limit=10)

    # 5. 检查并打印结果
    doc_count = len(results['ids'])
    print(f"✅ 集合 '{collection_name}' 存在。")
    print(f"📊 本次查询返回了 {doc_count} 条数据。")

    if doc_count > 0:
        print("📝 数据预览：")
        for i, doc_id in enumerate(results['ids']):
            print(f"  - ID: {doc_id}")
            if results['documents']:
                print(f"    文档内容: {results['documents'][i][:100]}...")  # 截取前100个字符
    else:
        print("⚠️ 集合存在，但目前没有任何数据。")

except ValueError as e:
    # 捕获集合不存在的情况
    print(f"❌ 错误: 集合 '{collection_name}' 不存在。")
except Exception as e:
    # 捕获其他连接或网络错误
    print(f"❌ 发生未知错误: {e}")