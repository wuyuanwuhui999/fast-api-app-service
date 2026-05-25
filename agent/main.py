from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent.routers import agent_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

# 创建数据库表（如果 agent 模块有独立模型，否则可以省略）
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)


@app.get("/")
async def root():
    return {"message": "Agent Service is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agent"}


def create_app():
    """创建应用（用于Nacos注册）"""
    return app

# 在 gateway/main.py 中添加 Agent WebSocket 路由

@app.websocket("/service/agent/ws/chat")
async def websocket_gateway_agent(
    websocket: WebSocket,
    token: str = None,
):
    """
    Agent WebSocket网关 - 代理WebSocket连接到agent服务
    
    前端连接方式:
    ws://localhost:4009/service/agent/ws/chat?token=xxx
    """
    
    logger.info(f"[AgentWebSocketGateway] ========== 收到WebSocket连接请求 ==========")
    logger.info(f"[AgentWebSocketGateway] token参数: {token[:100] if token else 'None'}...")
    
    # 1. 验证token并获取用户ID
    if not token:
        logger.error(f"[AgentWebSocketGateway] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token")
        return
    
    user_id = verify_token_and_get_user_id(token)
    
    if not user_id:
        logger.error(f"[AgentWebSocketGateway] token验证失败")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    logger.info(f"[AgentWebSocketGateway] ✅ token验证成功，用户ID: {user_id}")
    
    # 2. 获取agent服务实例
    service_name = "agent-service"
    logger.info(f"[AgentWebSocketGateway] 正在获取服务实例: {service_name}")
    
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[AgentWebSocketGateway] ❌ 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    logger.info(f"[AgentWebSocketGateway] ✅ 获取到服务实例: {instance['ip']}:{instance['port']}")
    
    # 3. 构建目标WebSocket URL（带上X-User-Id参数）
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/agent/ws/chat?X-User-Id={user_id}"
    logger.info(f"[AgentWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    # 4. 接受客户端WebSocket连接
    try:
        await websocket.accept()
        logger.info(f"[AgentWebSocketGateway] ✅ 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[AgentWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    # 5. 创建到目标服务的WebSocket连接并转发消息
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[AgentWebSocketGateway] ✅ 已连接到目标WebSocket服务")
        
        # 双向消息转发
        async def forward_to_target():
            try:
                while True:
                    message = await websocket.receive_text()
                    logger.debug(f"[AgentWebSocketGateway] 客户端 -> 目标: {message[:100]}...")
                    await target_websocket.send(message)
            except WebSocketDisconnect:
                logger.info(f"[AgentWebSocketGateway] 客户端WebSocket连接断开")
            except Exception as e:
                logger.error(f"[AgentWebSocketGateway] 转发到目标服务失败: {str(e)}")
            finally:
                if target_websocket:
                    await target_websocket.close()
        
        async def forward_to_client():
            try:
                while True:
                    message = await target_websocket.recv()
                    logger.debug(f"[AgentWebSocketGateway] 目标 -> 客户端: {message[:100]}...")
                    await websocket.send_text(message)
            except Exception as e:
                logger.error(f"[AgentWebSocketGateway] 转发到客户端失败: {str(e)}")
        
        await asyncio.gather(
            forward_to_target(),
            forward_to_client(),
            return_exceptions=True
        )
        
    except ws_lib.exceptions.WebSocketException as e:
        logger.error(f"[AgentWebSocketGateway] WebSocket连接错误: {str(e)}")
        try:
            await websocket.close(code=4002, reason=f"WebSocket connection error: {str(e)}")
        except:
            pass
    except Exception as e:
        logger.error(f"[AgentWebSocketGateway] WebSocket代理错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"WebSocket proxy error: {str(e)}")
        except:
            pass
    finally:
        if target_websocket:
            await target_websocket.close()
        logger.info(f"[AgentWebSocketGateway] WebSocket连接已关闭")
        
# 注册到Nacos
@service_registry.register(
    service_name="agent-service",
    port=3010,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=3010)