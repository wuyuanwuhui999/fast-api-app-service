# test/test_chat_websocket.py
"""
WebSocket 聊天接口测试脚本
测试 Chat Service 的 WebSocket 接口

直接修改下方配置参数即可运行
"""

import asyncio
import json
import websockets
import logging
import uuid
from datetime import datetime
import uuid

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ============================================================
# 配置参数 - 直接修改这里
# ============================================================
WS_URL = "ws://127.0.0.1:3006/service/chat/ws/chat"
USER_ID = "e991bfe7598e4ebeab3dd4af9b7d09b0"
DOC_IDS = ["35e71b56a39d40df88a6433562e426c1"]
MODEL_ID = "34b62e2a978811f09e6f002b67a509e7"
COMPANY_ID = "0d3cc1965bd811f18f407875e005753f"
CHAT_ID = uuid.uuid4().hex
DIRECTORY_ID = "e3361de7abe341778aa9e0ff0691aa25"
TENANT_ID = "f96f89c075d611f0be3b002b67a509e7"
PROMPT = "准考证号"
CHAT_TYPE = "document"  # document: 文档问答, normal: 普通聊天
SHOW_THINK = False  # 是否显示思考过程
SYSTEM_PROMPT = "你是一个专业的考试助手，请根据提供的文档内容回答问题。"
# ============================================================


async def test_chat_websocket():
    """
    测试 WebSocket 聊天接口
    """
    # 生成会话ID（如果未指定）
    chat_id = CHAT_ID or uuid.uuid4().hex
    
    # 构建 WebSocket URL（包含用户ID）
    ws_url = f"{WS_URL}?X-User-Id={USER_ID}"
    
    logger.info("=" * 70)
    logger.info("🚀 开始测试 WebSocket 聊天接口")
    logger.info("=" * 70)
    logger.info(f"  WebSocket URL: {ws_url}")
    logger.info(f"  用户ID: {USER_ID}")
    logger.info(f"  模型ID: {MODEL_ID}")
    logger.info(f"  会话ID: {chat_id}")
    logger.info(f"  目录ID: {DIRECTORY_ID}")
    logger.info(f"  租户ID: {TENANT_ID}")
    logger.info(f"  提示词: {PROMPT}")
    logger.info(f"  聊天类型: {CHAT_TYPE}")
    logger.info("=" * 70)
    
    websocket = None
    
    try:
        # 1. 建立 WebSocket 连接（移除 timeout 参数）
        logger.info("📡 正在连接 WebSocket...")
        websocket = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info("✅ WebSocket 连接成功！")
        
        # 2. 构建消息
        message = {
            "prompt": PROMPT,
            "type": CHAT_TYPE,
            "docIds": DOC_IDS,
            "chatId": chat_id,
            "modelId": MODEL_ID,
            "showThink": SHOW_THINK,
            "companyId": COMPANY_ID,
            "tenantId": TENANT_ID
        }
        
        # 如果是文档问答，添加系统提示词
        if CHAT_TYPE == "document":
            message["systemPrompt"] = SYSTEM_PROMPT
        
        # 3. 发送消息
        message_json = json.dumps(message, ensure_ascii=False)
        logger.info("📤 发送消息:")
        logger.info(json.dumps(message, ensure_ascii=False, indent=2))
        await websocket.send(message_json)
        logger.info("✅ 消息发送成功")
        
        # 4. 接收响应
        logger.info("📥 开始接收响应...")
        logger.info("-" * 60)
        print("\n🤖 助手: ", end="", flush=True)
        
        full_response = ""
        message_count = 0
        
        while True:
            try:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=60
                )
            except asyncio.TimeoutError:
                logger.warning("⏰ 接收消息超时")
                break
            
            # 检查是否为完成信号
            if response == "[completed]":
                logger.info("\n\n✅ 聊天完成")
                break
            
            # 检查是否为错误消息
            if response.startswith("Error:"):
                logger.error(f"\n❌ 服务端错误: {response}")
                break
            
            # 正常消息 - 实时打印
            message_count += 1
            full_response += response
            print(response, end="", flush=True)
        
        print("\n")
        logger.info("-" * 60)
        logger.info(f"📊 共收到 {message_count} 条消息片段")
        logger.info(f"📝 完整响应长度: {len(full_response)} 字符")
        
        # 5. 显示完整响应（可选）
        if full_response:
            logger.info("📄 完整响应内容:")
            logger.info("-" * 40)
            print(full_response)
            logger.info("-" * 40)
        
        return full_response
        
    except websockets.exceptions.ConnectionClosed as e:
        logger.error(f"❌ WebSocket 连接关闭: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}", exc_info=True)
        return ""
    finally:
        # 6. 关闭连接
        if websocket:
            try:
                await websocket.close()
                logger.info("🔌 WebSocket 连接已关闭")
            except Exception as e:
                logger.warning(f"关闭连接时出错: {str(e)}")


async def test_multi_round_chat():
    """
    测试多轮对话（使用相同的 chat_id 保持会话上下文）
    """
    chat_id = CHAT_ID or "multi_round_" + datetime.now().strftime("%Y%m%d%H%M%S")
    ws_url = f"{WS_URL}?X-User-Id={USER_ID}"
    
    logger.info("=" * 70)
    logger.info("🔄 开始测试多轮对话")
    logger.info("=" * 70)
    logger.info(f"  会话ID: {chat_id}")
    
    # 多轮对话的问题列表
    queries = [
        "投保人需要满足哪些条件？",
        "如果发生理赔，需要准备什么材料？",
        "续保流程是怎样的？"
    ]
    
    websocket = None
    responses = []
    
    try:
        # 建立连接（多轮对话复用同一个连接）
        logger.info("📡 正在连接 WebSocket...")
        websocket = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info("✅ WebSocket 连接成功！")
        
        for idx, query in enumerate(queries, 1):
            logger.info("")
            logger.info(f"--- 第 {idx} 轮对话 ---")
            logger.info(f"问题: {query}")
            
            # 构建消息
            message = {
                "prompt": query,
                "type": CHAT_TYPE,
                "directoryId": DIRECTORY_ID,
                "chatId": chat_id,
                "modelId": MODEL_ID,
                "showThink": SHOW_THINK,
                "tenant_id": TENANT_ID
            }
            
            if CHAT_TYPE == "document":
                message["systemPrompt"] = SYSTEM_PROMPT
            
            # 发送消息
            await websocket.send(json.dumps(message, ensure_ascii=False))
            
            # 接收响应
            print(f"\n🤖 回答 {idx}: ", end="", flush=True)
            full_response = ""
            message_count = 0
            
            while True:
                try:
                    response = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=60
                    )
                except asyncio.TimeoutError:
                    break
                
                if response == "[completed]":
                    break
                
                if response.startswith("Error:"):
                    logger.error(f"\n❌ 服务端错误: {response}")
                    break
                
                message_count += 1
                full_response += response
                print(response, end="", flush=True)
            
            print("\n")
            responses.append(full_response)
            logger.info(f"✅ 第 {idx} 轮完成，收到 {message_count} 条消息")
        
        return responses
        
    except Exception as e:
        logger.error(f"❌ 多轮对话失败: {str(e)}", exc_info=True)
        return []
    finally:
        if websocket:
            try:
                await websocket.close()
                logger.info("🔌 WebSocket 连接已关闭")
            except Exception:
                pass


async def interactive_chat():
    """
    交互式聊天模式
    """
    chat_id = CHAT_ID or "interactive_" + datetime.now().strftime("%Y%m%d%H%M%S")
    ws_url = f"{WS_URL}?X-User-Id={USER_ID}"
    
    logger.info("=" * 70)
    logger.info("🎤 进入交互式聊天模式")
    logger.info("   输入 'quit' 或 'exit' 退出")
    logger.info("   输入 'clear' 重置会话")
    logger.info("=" * 70)
    logger.info(f"  会话ID: {chat_id}")
    
    websocket = None
    
    try:
        # 建立连接
        logger.info("📡 正在连接 WebSocket...")
        websocket = await websockets.connect(
            ws_url,
            ping_interval=20,
            ping_timeout=10
        )
        logger.info("✅ WebSocket 连接成功！")
        logger.info("=" * 70)
        
        while True:
            try:
                prompt = input("\n👤 你: ").strip()
                if not prompt:
                    continue
                
                if prompt.lower() in ["quit", "exit", "q"]:
                    break
                
                if prompt.lower() == "clear":
                    chat_id = "interactive_" + datetime.now().strftime("%Y%m%d%H%M%S")
                    logger.info(f"🔄 已重置会话，新会话 ID: {chat_id}")
                    continue
                
                # 构建消息
                message = {
                    "prompt": prompt,
                    "type": CHAT_TYPE,
                    "directoryId": DIRECTORY_ID,
                    "chatId": chat_id,
                    "modelId": MODEL_ID,
                    "showThink": SHOW_THINK,
                    "tenant_id": TENANT_ID
                }
                
                if CHAT_TYPE == "document":
                    message["systemPrompt"] = SYSTEM_PROMPT
                
                # 发送消息
                await websocket.send(json.dumps(message, ensure_ascii=False))
                
                # 接收响应
                print("🤖 助手: ", end="", flush=True)
                full_response = ""
                
                while True:
                    try:
                        response = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=60
                        )
                    except asyncio.TimeoutError:
                        break
                    
                    if response == "[completed]":
                        break
                    
                    if response.startswith("Error:"):
                        logger.error(f"\n❌ 服务端错误: {response}")
                        break
                    
                    full_response += response
                    print(response, end="", flush=True)
                
                print()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"交互错误: {str(e)}")
                continue
        
    except Exception as e:
        logger.error(f"❌ 交互式聊天失败: {str(e)}", exc_info=True)
    finally:
        if websocket:
            try:
                await websocket.close()
                logger.info("🔌 WebSocket 连接已关闭")
            except Exception:
                pass
        logger.info("👋 交互式聊天已结束")


async def test_chat_with_timeout():
    """
    使用超时控制的 WebSocket 测试（使用 asyncio.wait_for 控制整体超时）
    """
    chat_id = CHAT_ID or uuid.uuid4().hex
    ws_url = f"{WS_URL}?X-User-Id={USER_ID}"
    
    logger.info("=" * 70)
    logger.info("🚀 开始测试 WebSocket 聊天接口（带超时控制）")
    logger.info("=" * 70)
    
    websocket = None
    
    try:
        # 1. 建立 WebSocket 连接（使用 asyncio.wait_for 控制连接超时）
        logger.info("📡 正在连接 WebSocket...")
        websocket = await asyncio.wait_for(
            websockets.connect(ws_url, ping_interval=20, ping_timeout=10),
            timeout=10
        )
        logger.info("✅ WebSocket 连接成功！")
        
        # 2. 构建并发送消息
        message = {
            "prompt": PROMPT,
            "type": CHAT_TYPE,
            "directoryId": DIRECTORY_ID,
            "chatId": chat_id,
            "modelId": MODEL_ID,
            "showThink": SHOW_THINK,
            "tenant_id": TENANT_ID
        }
        
        if CHAT_TYPE == "document":
            message["systemPrompt"] = SYSTEM_PROMPT
        
        logger.info("📤 发送消息...")
        await websocket.send(json.dumps(message, ensure_ascii=False))
        logger.info("✅ 消息发送成功")
        
        # 3. 接收响应
        logger.info("📥 开始接收响应...")
        print("\n🤖 助手: ", end="", flush=True)
        
        full_response = ""
        message_count = 0
        
        while True:
            try:
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=60
                )
            except asyncio.TimeoutError:
                logger.warning("⏰ 接收消息超时")
                break
            
            if response == "[completed]":
                logger.info("\n\n✅ 聊天完成")
                break
            
            if response.startswith("Error:"):
                logger.error(f"\n❌ 服务端错误: {response}")
                break
            
            message_count += 1
            full_response += response
            print(response, end="", flush=True)
        
        print("\n")
        logger.info("-" * 60)
        logger.info(f"📊 共收到 {message_count} 条消息片段")
        logger.info(f"📝 完整响应长度: {len(full_response)} 字符")
        
        return full_response
        
    except asyncio.TimeoutError:
        logger.error("❌ 连接超时")
        return ""
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}", exc_info=True)
        return ""
    finally:
        if websocket:
            try:
                await websocket.close()
                logger.info("🔌 WebSocket 连接已关闭")
            except Exception:
                pass


async def main():
    """主函数 - 直接运行即可"""
    # 选择测试模式：单次对话 / 多轮对话 / 交互式 / 带超时控制
    # 取消注释对应的行即可切换模式
    
    # 模式1：单次对话（默认）
    await test_chat_websocket()
    
    # 模式2：多轮对话
    # await test_multi_round_chat()
    
    # 模式3：交互式聊天
    # await interactive_chat()
    
    # 模式4：带超时控制的测试
    # await test_chat_with_timeout()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 测试已终止")
    except Exception as e:
        logger.error(f"❌ 测试执行失败: {str(e)}")