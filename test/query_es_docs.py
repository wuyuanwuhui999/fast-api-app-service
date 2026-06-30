# query_es_docs.py
import requests
import json
import os
import sys
from typing import Optional, Dict, Any, List


class ElasticsearchQuery:
    """Elasticsearch查询工具类"""
    
    def __init__(self, es_url: str = "http://localhost:9200", index_name: str = "chat_vector_index"):
        """
        初始化ES查询客户端
        
        Args:
            es_url: Elasticsearch服务地址
            index_name: 索引名称
        """
        self.es_url = es_url.rstrip('/')
        self.index_name = index_name
        
    def search_by_user_id(self, user_id: str, size: int = 10) -> Optional[Dict[str, Any]]:
        """
        根据用户ID查询文档
        
        Args:
            user_id: 用户ID
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        query = {
            "query": {
                "term": {
                    "metadata.user_id": user_id
                }
            },
            "size": size,
            "sort": [
                {"metadata.page": {"order": "asc"}}
            ]
        }
        return self._execute_search(query)
    
    def search_by_doc_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        根据文档ID查询
        
        Args:
            doc_id: 文档ID
            
        Returns:
            查询结果字典
        """
        query = {
            "query": {
                "term": {
                    "metadata.doc_id": doc_id
                }
            },
            "size": 100
        }
        return self._execute_search(query)
    
    def search_by_directory(self, directory_id: str, user_id: Optional[str] = None, size: int = 20) -> Optional[Dict[str, Any]]:
        """
        根据目录ID查询
        
        Args:
            directory_id: 目录ID
            user_id: 可选的用户ID过滤
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        must_terms = [
            {"term": {"metadata.directory_id": directory_id}}
        ]
        
        if user_id:
            must_terms.append({"term": {"metadata.user_id": user_id}})
        
        query = {
            "query": {
                "bool": {
                    "must": must_terms
                }
            },
            "size": size
        }
        return self._execute_search(query)
    
    def search_by_tenant(self, tenant_id: str, size: int = 20) -> Optional[Dict[str, Any]]:
        """
        根据租户ID查询
        
        Args:
            tenant_id: 租户ID
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        query = {
            "query": {
                "term": {
                    "metadata.tenant_id": tenant_id
                }
            },
            "size": size
        }
        return self._execute_search(query)
    
    def search_by_filename(self, filename: str, user_id: Optional[str] = None, size: int = 20) -> Optional[Dict[str, Any]]:
        """
        根据文件名模糊查询
        
        Args:
            filename: 文件名（支持部分匹配）
            user_id: 可选的用户ID过滤
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        must_queries = [
            {"match": {"metadata.filename": filename}}
        ]
        
        if user_id:
            must_queries.append({"term": {"metadata.user_id": user_id}})
        
        query = {
            "query": {
                "bool": {
                    "must": must_queries
                }
            },
            "size": size
        }
        return self._execute_search(query)
    
    def search_by_content(self, content: str, user_id: Optional[str] = None, size: int = 10) -> Optional[Dict[str, Any]]:
        """
        根据内容语义搜索
        
        Args:
            content: 搜索内容
            user_id: 可选的用户ID过滤
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        # 注意：这个查询用于普通搜索，不是向量搜索
        # 向量搜索需要使用专门的向量查询
        must_queries = [
            {"match": {"page_content": content}}
        ]
        
        if user_id:
            must_queries.append({"term": {"metadata.user_id": user_id}})
        
        query = {
            "query": {
                "bool": {
                    "must": must_queries
                }
            },
            "size": size
        }
        return self._execute_search(query)
    
    def get_all_docs(self, size: int = 50) -> Optional[Dict[str, Any]]:
        """
        获取所有文档（分页）
        
        Args:
            size: 返回结果数量
            
        Returns:
            查询结果字典
        """
        query = {
            "query": {
                "match_all": {}
            },
            "size": size,
            "sort": [
                {"_id": {"order": "desc"}}
            ]
        }
        return self._execute_search(query)
    
    def get_doc_count(self, user_id: Optional[str] = None) -> int:
        """
        获取文档总数
        
        Args:
            user_id: 可选的用户ID过滤
            
        Returns:
            文档总数
        """
        if user_id:
            query = {
                "query": {
                    "term": {
                        "metadata.user_id": user_id
                    }
                }
            }
        else:
            query = {
                "query": {
                    "match_all": {}
                }
            }
        
        try:
            url = f"{self.es_url}/{self.index_name}/_count"
            response = requests.post(url, json=query)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('count', 0)
            else:
                print(f"❌ 查询失败: {response.status_code}")
                return 0
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")
            return 0
    
    def _execute_search(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        执行搜索请求
        
        Args:
            query: 查询DSL
            
        Returns:
            查询结果
        """
        try:
            url = f"{self.es_url}/{self.index_name}/_search"
            response = requests.post(url, json=query)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 查询失败: {response.status_code}")
                print(f"响应内容: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print(f"❌ 连接失败: 无法连接到 {self.es_url}")
            print("提示: 请确保Elasticsearch服务已启动")
            return None
        except Exception as e:
            print(f"❌ 请求失败: {str(e)}")
            return None


def format_results(result: Dict[str, Any]) -> None:
    """
    格式化并打印查询结果
    
    Args:
        result: ES查询结果
    """
    if not result:
        print("❌ 没有查询到数据")
        return
    
    total = result.get('hits', {}).get('total', {})
    if isinstance(total, dict):
        total_count = total.get('value', 0)
    else:
        total_count = total
    
    hits = result.get('hits', {}).get('hits', [])
    
    print("=" * 70)
    print(f"📊 查询结果: 共找到 {total_count} 条记录")
    print("=" * 70)
    
    if not hits:
        print("❌ 未找到匹配的文档")
        return
    
    for i, hit in enumerate(hits, 1):
        source = hit.get('_source', {})
        metadata = source.get('metadata', {})
        page_content = source.get('page_content', '')
        
        print(f"\n📄 【文档 {i}】")
        print("-" * 50)
        print(f"  📁 文档ID: {metadata.get('doc_id', 'N/A')}")
        print(f"  📝 文件名: {metadata.get('filename', 'N/A')}")
        print(f"  👤 用户ID: {metadata.get('user_id', 'N/A')}")
        print(f"  🏢 租户ID: {metadata.get('tenant_id', 'N/A')}")
        print(f"  📂 目录ID: {metadata.get('directory_id', 'N/A')}")
        print(f"  📄 页码: {metadata.get('page', 'N/A')}")
        print(f"  📍 ES ID: {hit.get('_id', 'N/A')}")
        print(f"  📝 内容预览: {page_content[:100]}{'...' if len(page_content) > 100 else ''}")
        print(f"  📊 内容长度: {len(page_content)} 字符")
        print("-" * 50)


def check_es_status(es_url: str = "http://localhost:9200") -> bool:
    """
    检查Elasticsearch服务状态
    
    Args:
        es_url: ES服务地址
        
    Returns:
        服务是否可用
    """
    try:
        response = requests.get(f"{es_url.rstrip('/')}/_cluster/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Elasticsearch服务正常")
            print(f"  集群名称: {health.get('cluster_name', 'N/A')}")
            print(f"  状态: {health.get('status', 'N/A')}")
            print(f"  节点数: {health.get('number_of_nodes', 'N/A')}")
            return True
        else:
            print(f"❌ Elasticsearch服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到Elasticsearch: {str(e)}")
        return False


def main():
    """主函数"""
    
    # ====== 配置参数 ======
    
    # Elasticsearch配置
    ES_URL = "http://localhost:9200"
    INDEX_NAME = "chat_vector_index"
    
    # 查询参数
    USER_ID = "e991bfe7598e4ebeab3dd4af9b7d09b0"  # 你的用户ID
    
    # ====== 开始查询 ======
    
    print("=" * 70)
    print("🔍 Elasticsearch 文档查询工具")
    print("=" * 70)
    print()
    
    # 1. 检查ES服务状态
    print("📡 检查Elasticsearch服务状态...")
    if not check_es_status(ES_URL):
        print("\n❌ Elasticsearch服务不可用，请确保已启动ES")
        sys.exit(1)
    print()
    
    # 2. 初始化查询器
    es_query = ElasticsearchQuery(es_url=ES_URL, index_name=INDEX_NAME)
    
    # 3. 查询文档总数
    print("📊 查询索引统计信息...")
    total_count = es_query.get_doc_count()
    print(f"   📝 索引 {INDEX_NAME} 总文档数: {total_count}")
    
    if USER_ID:
        user_count = es_query.get_doc_count(user_id=USER_ID)
        print(f"   👤 用户 {USER_ID[:8]}... 的文档数: {user_count}")
    print()
    
    # 4. 根据用户ID查询
    print(f"🔍 查询用户 {USER_ID[:8]}... 的文档")
    print("-" * 70)
    
    result = es_query.search_by_user_id(USER_ID, size=20)
    
    if result:
        format_results(result)
    else:
        print("❌ 查询失败或没有数据")
    
    print("\n" + "=" * 70)
    
    # 5. 互动查询（可选）
    print("\n💡 提示：你可以使用以下方法进行自定义查询")
    print("   - search_by_doc_id(doc_id)")
    print("   - search_by_directory(directory_id, user_id)")
    print("   - search_by_filename(filename, user_id)")
    print("   - search_by_tenant(tenant_id)")
    print("   - get_all_docs(size)")


if __name__ == "__main__":
    main()