# test_agent_websocket.py
"""
测试Agent模块WebSocket接口
使用方法: python test_agent_websocket.py
"""

import asyncio
import websockets
import requests
import json
import uuid
import hashlib
from typing import Optional


class AgentWebSocketTester:
    """Agent WebSocket测试器"""
    
    def __init__(self, gateway_host: str = "localhost", gateway_port: int = 4009):
        self.gateway_url = f"http://{gateway_host}:{gateway_port}"
        self.ws_url = f"ws://{gateway_host}:{gateway_port}"
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
    
    @staticmethod
    def md5_encrypt(password: str) -> str:
        """
        将明文密码转换为MD5密文
        
        Args:
            password: 明文密码
            
        Returns:
            MD5加密后的密码（32位小写）
        """
        return hashlib.md5(password.encode('utf-8')).hexdigest()
    
    def login(self, user_account: str, password: str, use_md5: bool = True) -> bool:
        """
        调用登录接口获取token
        
        Args:
            user_account: 用户账号/邮箱/手机号
            password: 密码（明文或密文）
            use_md5: 是否将密码转换为MD5（默认True）
            
        Returns:
            bool: 登录是否成功
        """
        # 如果需要MD5加密，转换密码
        if use_md5:
            encrypted_password = self.md5_encrypt(password)
            print(f"\n🔐 密码加密: {password} -> {encrypted_password}")
        else:
            encrypted_password = password
        
        print(f"\n{'='*60}")
        print(f"🔐 正在登录: {user_account}")
        print(f"{'='*60}")
        
        login_url = f"{self.gateway_url}/service/user/login"
        
        login_data = {
            "userAccount": user_account,
            "password": encrypted_password
        }
        
        try:
            response = requests.post(
                login_url,
                json=login_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"📡 登录请求URL: {login_url}")
            print(f"📡 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"📡 响应内容: {json.dumps(result, ensure_ascii=False, indent=2)}")
                
                if result.get("status") == "SUCCESS":
                    self.token = result.get("token")
                    self.user_id = result.get("data", {}).get("id")
                    
                    print(f"\n✅ 登录成功!")
                    print(f"   - 用户ID: {self.user_id}")
                    print(f"   - Token: {self.token[:50]}..." if self.token else "   - Token: None")
                    return True
                else:
                    print(f"\n❌ 登录失败: {result.get('msg', '未知错误')}")
                    return False
            else:
                print(f"\n❌ HTTP请求失败: {response.status_code}")
                print(f"   响应: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ 无法连接到Gateway服务: {self.gateway_url}")
            print("   请确保Gateway服务已启动")
            return False
        except requests.exceptions.Timeout:
            print(f"\n❌ 登录请求超时")
            return False
        except Exception as e:
            print(f"\n❌ 登录异常: {str(e)}")
            return False
    
    async def test_websocket_chat(self, prompt: str, model_id: str, chat_id: str = None):
        """
        测试WebSocket聊天
        
        Args:
            prompt: 用户输入的问题（音乐相关）
            model_id: 模型ID（从chat_model表查询）
            chat_id: 会话ID（可选，不传则自动生成）
        """
        if not self.token:
            print("\n❌ 请先登录获取token")
            return
        
        if chat_id is None:
            chat_id = str(uuid.uuid4())[:8]
        
        print(f"\n{'='*60}")
        print(f"🎵 开始WebSocket聊天测试")
        print(f"{'='*60}")
        print(f"📝 用户问题: {prompt}")
        print(f"🆔 会话ID: {chat_id}")
        print(f"🤖 模型ID: {model_id}")
        
        # Token需要加上Bearer前缀
        token_with_bearer = f"Bearer {self.token}"
        # 构建WebSocket URL（带token参数）
        ws_full_url = f"{self.ws_url}/service/agent/ws/chat?token={token_with_bearer}"
        print(f"🔗 WebSocket地址: {ws_full_url[:100]}...")
        
        try:
            # 连接WebSocket（websockets库不支持timeout参数，使用asyncio.wait_for）
            print(f"\n🔌 正在连接WebSocket...")
            
            # 使用asyncio.wait_for设置连接超时
            async with asyncio.wait_for(
                websockets.connect(ws_full_url, close_timeout=10),
                timeout=30
            ) as websocket:
                print(f"✅ WebSocket连接成功!")
                
                # 构建发送消息
                message = {
                    "prompt": prompt,
                    "chatId": chat_id,
                    "modelId": model_id,
                    "showThink": False,
                    "tenant_id": "music",
                    "directoryId": "default"
                }
                
                print(f"\n📤 发送消息: {json.dumps(message, ensure_ascii=False)}")
                await websocket.send(json.dumps(message))
                print(f"✅ 消息已发送，等待响应...\n")
                print(f"{'='*60}")
                print(f"📋 响应内容:")
                print(f"{'='*60}")
                
                # 接收响应
                full_response = ""
                response_count = 0
                
                while True:
                    try:
                        # 使用asyncio.wait_for设置接收超时
                        response = await asyncio.wait_for(websocket.recv(), timeout=30)
                        response_count += 1
                        
                        # 检查是否完成
                        if response == "[completed]":
                            print(f"\n{'='*60}")
                            print(f"✅ 聊天完成! 共收到 {response_count} 条消息")
                            print(f"{'='*60}")
                            if full_response:
                                print(f"\n📋 完整响应内容:")
                                print(f"{'='*60}")
                                print(full_response)
                                print(f"{'='*60}")
                            break
                        else:
                            # 实时打印响应内容
                            print(f"{response}", end="", flush=True)
                            full_response += response
                            
                    except asyncio.TimeoutError:
                        print(f"\n⚠️ 接收超时 (30秒)")
                        break
                    except websockets.exceptions.ConnectionClosed as e:
                        print(f"\n⚠️ WebSocket连接已关闭: {e}")
                        break
                        
        except asyncio.TimeoutError:
            print(f"\n❌ 连接超时 (30秒)")
        except websockets.exceptions.InvalidURI as e:
            print(f"\n❌ 无效的WebSocket URI: {e}")
        except websockets.exceptions.WebSocketException as e:
            print(f"\n❌ WebSocket异常: {str(e)}")
        except Exception as e:
            print(f"\n❌ 未知异常: {str(e)}")
            import traceback
            traceback.print_exc()
    
    async def test_multiple_queries(self, model_id: str):
        """测试多个音乐查询"""
        test_queries = [
            "推荐几首周杰伦的歌",
            "有什么好听的粤语歌",
            "我心情不好，想听一些轻快的歌曲",
            "最近有什么热门歌曲",
            "推荐一些古典音乐",
            "你好，今天天气怎么样",  # 测试非音乐相关问题
        ]
        
        print(f"\n{'='*60}")
        print(f"🎯 开始批量测试 ({len(test_queries)}个问题)")
        print(f"{'='*60}")
        
        for i, query in enumerate(test_queries, 1):
            print(f"\n{'#'*60}")
            print(f"测试 {i}/{len(test_queries)}")
            await self.test_websocket_chat(query, model_id)
            await asyncio.sleep(2)  # 间隔2秒
    
    async def get_available_models(self) -> list:
        """获取可用的模型列表"""
        if not self.token:
            print("\n❌ 请先登录")
            return []
        
        print(f"\n{'='*60}")
        print(f"📋 获取可用模型列表")
        print(f"{'='*60}")
        
        models_url = f"{self.gateway_url}/service/chat/getModelList"
        
        try:
            response = requests.get(
                models_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "SUCCESS":
                    models = result.get("data", [])
                    print(f"\n✅ 可用模型列表:")
                    for model in models:
                        print(f"   - ID: {model.get('id')}")
                        print(f"     名称: {model.get('model_name')}")
                        print(f"     类型: {model.get('type')}")
                        print(f"     Base URL: {model.get('base_url')}")
                        print()
                    return models
                else:
                    print(f"\n❌ 获取模型列表失败: {result.get('msg')}")
                    return []
            else:
                print(f"\n❌ HTTP请求失败: {response.status_code}")
                return []
        except Exception as e:
            print(f"\n❌ 获取模型列表异常: {str(e)}")
            return []
    
    def test_md5(self, plain_password: str):
        """测试MD5加密功能"""
        encrypted = self.md5_encrypt(plain_password)
        print(f"\n📋 MD5加密测试:")
        print(f"   明文: {plain_password}")
        print(f"   密文: {encrypted}")
        print(f"   长度: {len(encrypted)}")
        return encrypted


async def run_test(
    user_account: str,
    password: str,
    model_id: str,
    prompt: str = "推荐几首好听的歌",
    gateway_host: str = "localhost",
    gateway_port: int = 4009,
    use_md5: bool = True
):
    """
    运行WebSocket测试
    
    Args:
        user_account: 用户账号
        password: 密码（明文）
        model_id: 模型ID
        prompt: 测试问题
        gateway_host: Gateway主机地址
        gateway_port: Gateway端口
        use_md5: 是否使用MD5加密（默认True）
    """
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║     Agent WebSocket 测试工具                                 ║
    ║                                                              ║
    ║     功能: 测试音乐查询WebSocket接口                          ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 创建测试器
    tester = AgentWebSocketTester(gateway_host, gateway_port)
    
    # 1. 登录获取token（自动MD5加密）
    if not tester.login(user_account, password, use_md5=use_md5):
        print("\n❌ 登录失败，测试终止")
        return
    
    # 2. 可选：获取可用模型列表
    await tester.get_available_models()
    
    # 3. 执行测试
    await tester.test_websocket_chat(prompt, model_id)


def test_with_custom_params(
    user_account: str,
    password: str,
    model_id: str,
    prompt: str = "推荐几首好听的歌",
    gateway_host: str = "localhost",
    gateway_port: int = 4009,
    use_md5: bool = True
):
    """
    使用自定义参数测试
    
    Args:
        user_account: 用户账号
        password: 密码（明文）
        model_id: 模型ID
        prompt: 测试问题
        gateway_host: Gateway主机地址（默认localhost）
        gateway_port: Gateway端口（默认4009）
        use_md5: 是否使用MD5加密（默认True）
    """
    asyncio.run(run_test(
        user_account=user_account,
        password=password,
        model_id=model_id,
        prompt=prompt,
        gateway_host=gateway_host,
        gateway_port=gateway_port,
        use_md5=use_md5
    ))


# ============================================================
# 辅助函数：生成密码的MD5值
# ============================================================

def get_md5_password(plain_password: str) -> str:
    """
    获取明文密码的MD5值（用于数据库存储或调试）
    
    Args:
        plain_password: 明文密码
        
    Returns:
        MD5加密后的密码
    """
    return hashlib.md5(plain_password.encode('utf-8')).hexdigest()


# ============================================================
# 直接在这里配置参数并运行测试
# ============================================================

if __name__ == "__main__":
    # ========== 配置参数（请根据实际情况修改）==========
    USER_ACCOUNT = "吴时吴刻"      # 替换为你的账号
    PASSWORD = "123456"         # 替换为你的密码
    MODEL_ID = "99d65a143a5811f199fe79c369c29396"         # 替换为实际的模型ID（从chat_model表查询）
    PROMPT = "我想听周杰伦的歌"         # 测试问题
    GATEWAY_HOST = "localhost"         # Gateway地址
    GATEWAY_PORT = 4009                # Gateway端口
    # ====================================================
    
    test_with_custom_params(
        user_account=USER_ACCOUNT,
        password=PASSWORD,
        model_id=MODEL_ID,
        prompt=PROMPT,
        gateway_host=GATEWAY_HOST,
        gateway_port=GATEWAY_PORT
    )