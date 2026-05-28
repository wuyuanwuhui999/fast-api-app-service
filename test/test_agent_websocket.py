#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import websockets
from typing import Optional


class AgentWebSocketClient:
    def __init__(self, uri: str):
        self.uri = uri
        self.websocket = None
    
    async def connect(self) -> bool:
        try:
            self.websocket = await websockets.connect(
                self.uri,
                ping_interval=30,
                ping_timeout=10
            )
            print(f"✅ WebSocket 连接成功")
            return True
        except Exception as e:
            print(f"❌ WebSocket 连接失败: {str(e)}")
            return False
    
    async def send_message(self, prompt: str, chat_id: str, model_id: str, tenant_id: str = "music"):
        message = {
            "prompt": prompt,
            "directoryId": "default",
            "chatId": chat_id,
            "modelId": model_id,
            "showThink": True,
            "tenant_id": tenant_id,
            "type": None,
            "language": None
        }
        
        print(f"\n📤 发送消息:")
        print(f"   prompt: {prompt}")
        print(f"   chatId: {chat_id}")
        print(f"   modelId: {model_id}")
        print(f"   tenant_id: {tenant_id}")
        
        await self.websocket.send(json.dumps(message))
        print("✅ 消息已发送，等待响应...\n")
    
    async def receive_response(self) -> Optional[str]:
        full_response = ""
        
        try:
            while True:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=60)
                
                if response == "[completed]":
                    print("\n✅ 聊天完成")
                    break
                elif response.startswith("Error:"):
                    print(f"\n❌ 收到错误: {response}")
                    break
                else:
                    print(response, end="", flush=True)
                    full_response += response
            
            print()
            return full_response
            
        except asyncio.TimeoutError:
            print("\n⚠️ 接收响应超时")
            return None
        except websockets.exceptions.ConnectionClosed:
            print("\n⚠️ WebSocket 连接已关闭")
            return None
    
    async def close(self):
        if self.websocket:
            await self.websocket.close()
            print("\n🔌 WebSocket 连接已关闭")


async def test_direct_agent(
    user_id: str = "f71d6c016fa94cd29f9db53f71ec7b62",
    prompt: str = "我想听周杰伦的歌",
    chat_id: str = "2043195f",
    model_id: str = "99d65a143a5811f199fe79c369c29396",
    tenant_id: str = "music"
):
    print("=" * 70)
    print("🚀 测试方式1: 直接调用 Agent 模块原接口")
    print("=" * 70)
    
    uri = f"ws://localhost:4010/service/agent/ws/chat?X-User-Id={user_id}"
    print(f"📡 连接地址: {uri}")
    print("-" * 70)
    
    client = AgentWebSocketClient(uri)
    
    if not await client.connect():
        return
    
    try:
        await client.send_message(prompt, chat_id, model_id, tenant_id)
        response = await client.receive_response()
        if response:
            print(f"\n📝 完整响应长度: {len(response)} 字符")
    finally:
        await client.close()


async def test_gateway_agent(
    token: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ7XCJ1c2VyQWNjb3VudFwiOiBcIlx1NTQzNFx1NjVmNlx1NTQzNFx1NTIzYlwiLCBcImVtYWlsXCI6IFwiMjc1MDE4NzIzQHFxLmNvbVwiLCBcInVzZXJuYW1lXCI6IFwiXHU1NDM0XHU2NWY2XHU1NDM0XHU1MjNiXCIsIFwiaWRcIjogXCJmNzFkNmMwMTZmYTk0Y2QyOWY5ZGI1M2Y3MWVjN2I2MlwiLCBcImNyZWF0ZURhdGVcIjogXCIyMDE5LTA4LTEyVDAwOjAwOjAwXCIsIFwidXBkYXRlRGF0ZVwiOiBcIjIwMjYtMDQtMTNUMDc6Mzk6MjVcIiwgXCJ0ZWxlcGhvbmVcIjogXCIxNTMwMjY4Njk0N1wiLCBcImF2YXRlclwiOiBcIi9zdGF0aWMvdXNlci9hdmF0ZXIvXHU1NDM0XHU2NWY2XHU1NDM0XHU1MjNiLmpwZ1wiLCBcImJpcnRoZGF5XCI6IFwiMTk5MC0xMC04XCIsIFwic2V4XCI6IFwiMFwiLCBcInJvbGVcIjogXCJwdWJsaWNcIiwgXCJzaWduXCI6IFwiXHU2NWUwXHU2NWY2XHU2NWUwXHU1MjNiXHU0ZTBkXHU2MGYzXHU0ZjYwXCIsIFwicmVnaW9uXCI6IG51bGwsIFwiZGlzYWJsZWRcIjogMCwgXCJwZXJtaXNzaW9uXCI6IDB9IiwiZXhwIjoxNzgyNTcwNjkyfQ.ulBpqMs1F4bDTsi2HII6dT8hGTEgD-khEfEEWGrJRac",
    prompt: str = "我想听周杰伦的歌",
    chat_id: str = "2043195f",
    model_id: str = "99d65a143a5811f199fe79c369c29396",
    tenant_id: str = "music"
):
    print("=" * 70)
    print("🚀 测试方式2: 通过 Gateway 网关调用 Agent 模块接口")
    print("=" * 70)
    
    uri = f"ws://localhost:4009/service/agent/ws/chat?token={token}"
    print(f"📡 连接地址: {uri[:100]}...")
    print("-" * 70)
    
    client = AgentWebSocketClient(uri)
    
    if not await client.connect():
        return
    
    try:
        await client.send_message(prompt, chat_id, model_id, tenant_id)
        response = await client.receive_response()
        if response:
            print(f"\n📝 完整响应长度: {len(response)} 字符")
    finally:
        await client.close()


async def main():
    print("\n" + "=" * 70)
    print("🎯 Agent WebSocket 接口测试")
    print("=" * 70)
    
    await test_direct_agent()
    
    print("\n" + "=" * 70)
    print("等待 2 秒后开始 Gateway 测试...")
    await asyncio.sleep(2)
    
    await test_gateway_agent()


if __name__ == "__main__":
    asyncio.run(main())