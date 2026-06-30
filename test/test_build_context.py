# test/test_build_context.py
"""
独立测试 build_context 方法的脚本
参数已直接写在方法调用中
"""
import asyncio
import sys
import os
import json
import logging
from pathlib import Path
from langchain_ollama import OllamaEmbeddings

# ============ 重要：添加项目根目录到 Python 路径 ============
# 获取项目根目录（test 目录的父目录）
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
# ============================================================

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

from sqlalchemy.orm import Session
from common.config.common_database import SessionLocal
from chat.services.chat_service import ChatService
from elasticsearch import Elasticsearch

# ============ 全局配置参数 ============
ES_HOST = "http://localhost:9200"
INDEX_NAME = "chat_vector_index"
DEFAULT_SIZE = 5
EMBEDDING_MODEL = "nomic-embed-text:latest"
# ===================================

# ============ 直接设置的测试参数 ============
TEST_USER_ID = "e991bfe7598e4ebeab3dd4af9b7d09b0"
TEST_DIRECTORY_ID = "e3361de7abe341778aa9e0ff0691aa25"
TEST_QUERY = "投保人"
TEST_TENANT_ID = None  # 可选，如果需要可以设置
# =========================================


async def build_context(
    query: str,
    user_id: str,
    directory_id: str,
    tenant_id: str = None
) -> str:
    """
    执行 Elasticsearch 向量相似度查询，返回字符串结果
    
    Args:
        query: 查询文本
        user_id: 用户ID
        directory_id: 目录ID
        tenant_id: 租户ID (可选)
    
    Returns:
        格式化的查询结果字符串，如果没有匹配结果则返回空字符串
    """
    es_client = None
    try:
        # 构建过滤条件
        must_conditions = [
            {"term": {"metadata.user_id": user_id}},
            {"term": {"metadata.directory_id": directory_id}}
        ]
        
        if tenant_id:
            must_conditions.append({"term": {"metadata.tenant_id": tenant_id}})
                        
        # 按需创建 Elasticsearch 客户端
        es_client = Elasticsearch(
            hosts=["http://localhost:9200"],
            request_timeout=10
        )
        
        # 按需创建 embedding 模型
        embedding_model = OllamaEmbeddings(model="nomic-embed-text:latest")
        query_embedding = embedding_model.embed_query(query)
        
        script_query = {
            "size": 5,
            "query": {
                "script_score": {
                    "query": {
                        "bool": {
                            "must": must_conditions
                        }
                    },
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'vector') + 1.0",
                        "params": {
                            "query_vector": query_embedding
                        }
                    }
                }
            },
            "_source": ["text", "metadata.filename", "metadata.page"]
        }
        
        response = es_client.search(index="chat_vector_index", body=script_query)
        hits = response.get('hits', {}).get('hits', [])
        
        if not hits:
            return ""  # 没有匹配结果，返回空字符串
        
        output_lines = ["以下是一些相关的文档摘录，可能有助于回答您的问题:\n"]
        for idx, hit in enumerate(hits):
            source = hit.get('_source', {})
            filename = source.get('metadata', {}).get('filename', '未知文件')
            text = source.get('text', '')
            text_preview = text[:50] + '...' if len(text) > 50 else text
            output_lines.append(f"第{idx+1}段, 文档来源：{filename}, 内容：{text_preview}\n\n")
        
        return "\n".join(output_lines)
        
    except Exception as e:
        logger.error(f"Elasticsearch 查询失败: {str(e)}", exc_info=True)
        return ""  # 查询失败，返回空字符串
    finally:
        if es_client:
            es_client.close()


async def main():
    """主函数"""
    # 直接使用预设参数执行测试
    result_str = await build_context(
        query=TEST_QUERY,
        user_id=TEST_USER_ID,
        directory_id=TEST_DIRECTORY_ID,
        tenant_id=TEST_TENANT_ID
    )
    
    # 打印结果
    print(result_str)
    
    return result_str


if __name__ == "__main__":
    asyncio.run(main())