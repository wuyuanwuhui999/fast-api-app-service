import chromadb

# 连接到你的本地 Chroma 服务
client = chromadb.HttpClient(host="localhost", port=8000)

# 删除集合
try:
    client.delete_collection(name="chat_vector_collection")
    print("集合 chat_vector_collection 删除成功！")
except Exception as e:
    print(f"删除失败: {e}")