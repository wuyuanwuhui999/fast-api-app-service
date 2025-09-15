from elasticsearch import Elasticsearch

# 连接到 Elasticsearch
es = Elasticsearch("http://localhost:9200")

# 检查连接
if not es.ping():
    print("无法连接到 Elasticsearch！")
    exit()


def search_documents(index_name, user_id=None, doc_id=None, directory_id=None, size=1000):
    """
    根据 metadata.user_id、metadata.doc_id 或 metadata.app_id 查询文档
    可以单独使用一个条件，也可以组合多个条件进行联合查询

    参数:
        index_name: 索引名称
        user_id: 要查询的用户ID (可选)
        doc_id: 要查询的文档ID (可选)
        app_id: 要查询的应用ID (可选)
        size: 返回的最大文档数量 (默认1000)
    """
    # 构建查询条件
    if user_id or doc_id or directory_id:
        query = {"bool": {"filter": []}}

        # 添加各个条件的过滤
        if user_id:
            query["bool"]["filter"].append({"term": {"metadata.user_id": user_id}})
        if doc_id:
            query["bool"]["filter"].append({"term": {"metadata.doc_id": doc_id}})
        if directory_id:
            query["bool"]["filter"].append({"term": {"metadata.directory_id": directory_id}})

        # 如果只有一个过滤条件，简化查询结构
        if len(query["bool"]["filter"]) == 1:
            query["bool"]["filter"] = query["bool"]["filter"][0]
    else:
        # 如果没有任何条件，则查询全部
        query = {"match_all": {}}

    # 完整的查询体
    body = {
        "query": query,
        "size": size
    }

    try:
        # 执行搜索
        response = es.search(index=index_name, body=body)

        # 处理结果
        hits = response['hits']['hits']
        if not hits:
            print(f"索引 '{index_name}' 中没有找到匹配的文档。")
            return []

        # 打印每个文档内容（可选）
        for hit in hits:
            print(hit["_source"])

        # 返回文档内容列表
        documents = [hit['_source'] for hit in hits]
        print(f"找到 {len(documents)} 个文档")
        return documents

    except Exception as e:
        print(f"查询索引 '{index_name}' 时出错: {e}")
        return []

def delete_all(index_name):
    """
    使用 delete_by_query 删除索引中的所有文档（注意：不会删除索引本身）
    """
    query = {
        "query": {
            "match_all": {}
        }
    }
    if not es.indices.exists(index=index_name):
        return print(f"索引 {index_name} 不存在")

    try:
        response = es.delete_by_query(index=index_name, body=query)
        print(f"已删除索引 '{index_name}' 中的 {response['deleted']} 个文档。")
    except Exception as e:
        print(f"删除索引 '{index_name}' 中的文档时出错: {e}")

def create_index(index_name):
    # 创建空索引（不指定 settings 和 mappings）
    if not es.indices.exists(index=index_name):
        # 如果索引不存在，则创建
        es.indices.create(index=index_name)  # 修正：传入 index_name 而不是空字符串
        print(f"索引 '{index_name}' 创建成功（为空索引）")
    else:
        print(f"索引 '{index_name}' 已存在，无需创建")


def delete_by_user_or_doc_id(index_name, user_id=None, doc_id=None):
    """
    根据 metadata.user_id 或 metadata.docId 删除文档

    参数:
        index_name: 索引名称
        user_id: 要删除的用户ID (可选)
        doc_id: 要删除的文档ID (可选)

    注意: 至少需要提供 user_id 或 doc_id 中的一个
    """
    if not user_id and not doc_id:
        print("错误: 必须提供 user_id 或 doc_id 中的一个")
        return

    # 构建查询条件
    query = {"bool": {}}

    if user_id and doc_id:
        query["bool"]["should"] = [
            {"term": {"metadata.user_id": user_id}},
            {"term": {"metadata.doc_id": doc_id}}
        ]
        query["bool"]["minimum_should_match"] = 1
    elif user_id:
        query["bool"]["filter"] = {"term": {"metadata.user_id": user_id}}
    elif doc_id:
        query["bool"]["filter"] = {"term": {"metadata.doc_id": doc_id}}

    try:
        # 执行删除操作
        response = es.delete_by_query(
            index=index_name,
            body={"query": query},
            conflicts="proceed",  # 遇到冲突继续执行
            refresh=True  # 立即刷新索引使删除结果立即可见
        )

        print(f"成功删除 {response['deleted']} 个文档")
        return response['deleted']
    except Exception as e:
        print(f"删除文档时出错: {e}")
        return 0

def get_mappering(index_name):
    # 获取索引映射
    try:
        mapping = es.indices.get_mapping(index=index_name)
        print(f"索引 '{index_name}' 的映射:")
        print(mapping)
    except Exception as e:
        print(f"获取映射失败: {e}")

index_name = "chat_vector_index"

# 创建索引（如果需要）
# create_index(index_name)

# 搜索所有文档
# search_documents(index_name)
# search_documents(index_name,user_id="f71d6c016fa94cd29f9db53f71ec7b62")

# get_mappering(index_name)

# 删除文档
delete_by_user_or_doc_id(index_name,user_id="f71d6c016fa94cd29f9db53f71ec7b62")
