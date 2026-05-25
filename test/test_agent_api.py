#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent模块API测试脚本
通过Gateway网关调用 /service/agent/getChatHistory 接口
支持MD5密码加密
"""

import requests
import json
import hashlib
from typing import Optional, Dict, Any

# 配置
GATEWAY_BASE_URL = "http://localhost:4009"
API_PATH = "/service/agent/getChatHistory"
TEST_TOKEN = None  # 需要替换为实际的JWT Token


def md5_encrypt(password: str) -> str:
    """
    对密码进行MD5加密
    
    Args:
        password: 明文密码
        
    Returns:
        MD5加密后的密码字符串（32位小写）
    """
    return hashlib.md5(password.encode('utf-8')).hexdigest()


def get_test_token(username: str = None, password: str = None) -> str:
    """
    获取测试用的JWT Token
    方式1: 通过登录接口获取（自动MD5加密密码）
    方式2: 直接使用已有的token
    
    Args:
        username: 用户名
        password: 明文密码（会自动MD5加密）
        
    Returns:
        JWT Token
    """
    # 方式1: 通过登录接口获取token
    if username and password:
        login_url = f"{GATEWAY_BASE_URL}/service/user/login"
        
        # MD5加密密码
        encrypted_password = md5_encrypt(password)
        
        login_data = {
            "userAccount": username,
            "password": encrypted_password  # 使用MD5加密后的密码
        }
        
        print(f"\n🔐 登录信息:")
        print(f"   用户名: {username}")
        print(f"   明文密码: {password}")
        print(f"   MD5密码: {encrypted_password}")
        
        try:
            response = requests.post(login_url, json=login_data, timeout=10)
            print(f"   登录响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                token = result.get("token")
                if token:
                    print(f"✅ 登录成功，获取到token: {token[:50]}...")
                    return token
                else:
                    print(f"❌ 登录响应中未找到token: {result}")
            else:
                print(f"❌ 登录失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ 登录请求异常: {e}")
    
    # 方式2: 直接使用已有的token（适用于测试）
    print("\n⚠️ 使用预设token（请确保token有效）")
    return "your_jwt_token_here"  # 替换为实际token


def get_chat_history(
    page_num: int = 1,
    page_size: int = 10,
    token: Optional[str] = None,
    base_url: str = GATEWAY_BASE_URL
) -> Dict[str, Any]:
    """
    调用getChatHistory接口
    
    Args:
        page_num: 页码，从1开始
        page_size: 每页记录数
        token: JWT Token
        base_url: Gateway基础URL
        
    Returns:
        接口返回的JSON数据
    """
    url = f"{base_url}{API_PATH}"
    
    # 请求参数
    params = {
        "pageNum": page_num,
        "pageSize": page_size
    }
    
    # 请求头
    headers = {
        "Content-Type": "application/json"
    }
    
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    print(f"\n{'='*60}")
    print(f"📤 发送请求")
    print(f"   URL: {url}")
    print(f"   Method: GET")
    print(f"   Params: {params}")
    print(f"   Headers: {headers}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        
        print(f"\n📥 接收响应")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response.elapsed.total_seconds():.3f}s")
        
        # 解析响应
        if response.status_code == 200:
            result = response.json()
            print(f"\n📋 响应数据:")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return result
        else:
            print(f"\n❌ 请求失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            return {"error": f"HTTP {response.status_code}", "detail": response.text}
            
    except requests.exceptions.ConnectionError:
        error_msg = f"无法连接到Gateway服务: {base_url}"
        print(f"\n❌ {error_msg}")
        print("   请确保Gateway服务已启动")
        return {"error": error_msg}
        
    except requests.exceptions.Timeout:
        error_msg = "请求超时"
        print(f"\n❌ {error_msg}")
        return {"error": error_msg}
        
    except Exception as e:
        error_msg = f"请求异常: {str(e)}"
        print(f"\n❌ {error_msg}")
        return {"error": error_msg}


def test_pagination(token: str):
    """测试分页功能"""
    print("\n" + "="*60)
    print("📖 测试分页功能")
    print("="*60)
    
    # 测试第1页，每页5条
    result_page1 = get_chat_history(page_num=1, page_size=5, token=token)
    
    # 测试第2页，每页5条
    result_page2 = get_chat_history(page_num=2, page_size=5, token=token)
    
    # 打印统计信息
    if "total" in result_page1:
        print(f"\n📊 统计信息:")
        print(f"   总记录数: {result_page1.get('total')}")
        print(f"   第1页数据量: {len(result_page1.get('data', []))}")
        print(f"   第2页数据量: {len(result_page2.get('data', []))}")


def test_different_page_sizes(token: str):
    """测试不同每页数量"""
    print("\n" + "="*60)
    print("📏 测试不同每页数量")
    print("="*60)
    
    for page_size in [5, 10, 20]:
        result = get_chat_history(page_num=1, page_size=page_size, token=token)
        data_count = len(result.get("data", []))
        print(f"\n   pageSize={page_size}: 返回 {data_count} 条记录")


def check_gateway_health() -> bool:
    """检查Gateway服务是否可用"""
    url = f"{GATEWAY_BASE_URL}/health"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("✅ Gateway服务健康检查通过")
            return True
        else:
            print(f"❌ Gateway服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Gateway服务不可用: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 Agent模块API测试")
    print("="*60)
    
    # 1. 检查Gateway服务
    if not check_gateway_health():
        print("\n请先启动Gateway服务:")
        print("  python -m uvicorn gateway.main:app --reload --port 4009 --host 0.0.0.0")
        return
    
    # 2. 配置登录信息（请修改为实际的用户名和密码）
    USERNAME = "your_username"  # 修改为实际用户名
    PASSWORD = "your_password"  # 修改为实际密码（明文，会自动MD5加密）
    
    # 3. 获取Token
    token = get_test_token(username=USERNAME, password=PASSWORD)
    
    if not token or token == "your_jwt_token_here":
        print("\n⚠️ 请设置有效的登录信息")
        print("   1. 修改脚本中的 USERNAME 和 PASSWORD 变量")
        print("   2. 或者直接设置 TEST_TOKEN 变量为有效的token")
        return
    
    # 4. 测试基础查询
    print("\n" + "="*60)
    print("🔍 测试基础查询")
    print("="*60)
    result = get_chat_history(page_num=1, page_size=10, token=token)
    
    # 5. 测试分页（如果有数据）
    if result.get("status") == "SUCCESS":
        test_pagination(token)
        test_different_page_sizes(token)
    
    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)


class AgentAPITester:
    """Agent API测试类"""
    
    def __init__(self, base_url: str = GATEWAY_BASE_URL, token: str = None):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()
    
    def set_token(self, token: str):
        """设置认证token"""
        self.token = token
    
    @staticmethod
    def md5_encrypt(password: str) -> str:
        """MD5加密密码"""
        return hashlib.md5(password.encode('utf-8')).hexdigest()
    
    def login(self, username: str, password: str) -> bool:
        """
        通过登录获取token（自动MD5加密密码）
        
        Args:
            username: 用户名
            password: 明文密码
            
        Returns:
            是否登录成功
        """
        url = f"{self.base_url}/service/user/login"
        
        # MD5加密密码
        encrypted_password = self.md5_encrypt(password)
        
        data = {
            "userAccount": username,
            "password": encrypted_password
        }
        
        print(f"\n🔐 登录请求:")
        print(f"   用户名: {username}")
        print(f"   MD5密码: {encrypted_password}")
        
        try:
            response = self.session.post(url, json=data, timeout=10)
            if response.status_code == 200:
                result = response.json()
                self.token = result.get("token")
                if self.token:
                    print(f"✅ 登录成功")
                    return True
            print(f"❌ 登录失败: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ 登录异常: {e}")
        return False
    
    def get_chat_history(
        self,
        page_num: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """获取聊天历史"""
        url = f"{self.base_url}{API_PATH}"
        params = {"pageNum": page_num, "pageSize": page_size}
        headers = {}
        
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "FAIL", "error": f"HTTP {response.status_code}"}
        except Exception as e:
            return {"status": "FAIL", "error": str(e)}
    
    def print_all_pages(self, page_size: int = 10):
        """打印所有页的数据"""
        page_num = 1
        total_pages = None
        
        while True:
            result = self.get_chat_history(page_num, page_size)
            
            if result.get("status") != "SUCCESS":
                break
            
            data = result.get("data", [])
            total = result.get("total", 0)
            
            if total_pages is None and total > 0:
                total_pages = (total + page_size - 1) // page_size
            
            print(f"\n--- 第 {page_num} 页 (共 {total_pages} 页) ---")
            for item in data:
                print(f"  ID: {item.get('id')}, Chat ID: {item.get('chat_id')}, Time: {item.get('create_time')}")
            
            if len(data) < page_size:
                break
            
            page_num += 1


# MD5加密工具函数
def encrypt_password_md5(password: str) -> str:
    """
    独立的MD5加密函数
    
    Args:
        password: 明文密码
        
    Returns:
        MD5加密后的密码（32位小写）
    """
    return hashlib.md5(password.encode('utf-8')).hexdigest()


if __name__ == "__main__":
    # 方式1: 直接运行主函数
    # main()
    
    # 方式2: 使用测试类
    tester = AgentAPITester()
    if tester.login("吴时吴刻", "123456"):
        result = tester.get_chat_history(page_num=1, page_size=10)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        tester.print_all_pages(page_size=5)
    
    # 方式3: 仅测试MD5加密
    # test_password = "123456"
    # print(f"明文密码: {test_password}")
    # print(f"MD5加密: {encrypt_password_md5(test_password)}")