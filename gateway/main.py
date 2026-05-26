# gateway/main.py - 完整修复版本
from fastapi import FastAPI, Request, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from typing import Optional
import logging
from contextlib import asynccontextmanager
import json

from gateway.middleware.auth_middleware import AuthMiddleware
from gateway.middleware.log_middleware import LogMiddleware
from gateway.services.route_service import RouteService
from common.utils.service_registry import service_registry
from common.config.common_config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("Gateway服务启动中...")
    yield
    logger.info("Gateway服务关闭...")


app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证中间件（最先执行，验证token并提取用户信息）
app.add_middleware(AuthMiddleware)

# 添加日志中间件（记录请求响应）
app.add_middleware(LogMiddleware)

# 初始化路由服务
route_service = RouteService()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}


@app.websocket("/service/chat/ws/chat")
async def websocket_gateway_chat(
    websocket: WebSocket,
):
    """
    Chat WebSocket网关 - 代理WebSocket连接到chat服务
    
    认证已在 AuthMiddleware 中完成，用户ID通过 X-User-Id 查询参数传递
    """
    
    logger.info(f"[ChatWebSocketGateway] ========== 收到WebSocket连接请求 ==========")
    
    # 从请求的query参数获取用户ID（由AuthMiddleware设置）
    user_id = websocket.query_params.get("X-User-Id")
    
    if not user_id:
        logger.error(f"[ChatWebSocketGateway] 未提供用户ID")
        await websocket.close(code=4001, reason="Missing user id")
        return
    
    logger.info(f"[ChatWebSocketGateway] ✅ 用户ID: {user_id}")
    
    # 获取chat服务实例
    service_name = "chat-service"
    logger.info(f"[ChatWebSocketGateway] 正在获取服务实例: {service_name}")
    
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[ChatWebSocketGateway] ❌ 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    logger.info(f"[ChatWebSocketGateway] ✅ 获取到服务实例: {instance['ip']}:{instance['port']}")
    
    # 构建目标WebSocket URL（带上X-User-Id参数）
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/chat/ws/chat?X-User-Id={user_id}"
    logger.info(f"[ChatWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    # 接受客户端WebSocket连接
    try:
        await websocket.accept()
        logger.info(f"[ChatWebSocketGateway] ✅ 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[ChatWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    # 创建到目标服务的WebSocket连接并转发消息
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[ChatWebSocketGateway] ✅ 已连接到目标WebSocket服务")
        
        # 双向消息转发
        async def forward_to_target():
            try:
                while True:
                    message = await websocket.receive_text()
                    logger.debug(f"[ChatWebSocketGateway] 客户端 -> 目标: {message[:100]}...")
                    await target_websocket.send(message)
            except WebSocketDisconnect:
                logger.info(f"[ChatWebSocketGateway] 客户端WebSocket连接断开")
            except Exception as e:
                logger.error(f"[ChatWebSocketGateway] 转发到目标服务失败: {str(e)}")
            finally:
                if target_websocket:
                    await target_websocket.close()
        
        async def forward_to_client():
            try:
                while True:
                    message = await target_websocket.recv()
                    logger.debug(f"[ChatWebSocketGateway] 目标 -> 客户端: {message[:100]}...")
                    await websocket.send_text(message)
            except Exception as e:
                logger.error(f"[ChatWebSocketGateway] 转发到客户端失败: {str(e)}")
        
        await asyncio.gather(
            forward_to_target(),
            forward_to_client(),
            return_exceptions=True
        )
        
    except ws_lib.exceptions.WebSocketException as e:
        logger.error(f"[ChatWebSocketGateway] WebSocket连接错误: {str(e)}")
        try:
            await websocket.close(code=4002, reason=f"WebSocket connection error: {str(e)}")
        except:
            pass
    except Exception as e:
        logger.error(f"[ChatWebSocketGateway] WebSocket代理错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"WebSocket proxy error: {str(e)}")
        except:
            pass
    finally:
        if target_websocket:
            await target_websocket.close()
        logger.info(f"[ChatWebSocketGateway] WebSocket连接已关闭")


@app.websocket("/service/agent/ws/chat")
async def websocket_gateway_agent(
    websocket: WebSocket,
):
    """
    Agent WebSocket网关 - 代理WebSocket连接到agent服务
    
    认证已在 AuthMiddleware 中完成，用户ID通过 X-User-Id 查询参数传递
    """
    
    logger.info(f"[AgentWebSocketGateway] ========== 收到WebSocket连接请求 ==========")
    
    # 从请求的query参数获取用户ID（由AuthMiddleware设置）
    user_id = websocket.query_params.get("X-User-Id")
    
    if not user_id:
        logger.error(f"[AgentWebSocketGateway] 未提供用户ID")
        await websocket.close(code=4001, reason="Missing user id")
        return
    
    logger.info(f"[AgentWebSocketGateway] ✅ 用户ID: {user_id}")
    
    # 获取agent服务实例
    service_name = "agent-service"
    logger.info(f"[AgentWebSocketGateway] 正在获取服务实例: {service_name}")
    
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[AgentWebSocketGateway] ❌ 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    logger.info(f"[AgentWebSocketGateway] ✅ 获取到服务实例: {instance['ip']}:{instance['port']}")
    
    # 构建目标WebSocket URL（带上X-User-Id参数）
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/agent/ws/chat?X-User-Id={user_id}"
    logger.info(f"[AgentWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    # 接受客户端WebSocket连接
    try:
        await websocket.accept()
        logger.info(f"[AgentWebSocketGateway] ✅ 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[AgentWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    # 创建到目标服务的WebSocket连接并转发消息
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


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway(request: Request, path: str):
    """网关核心路由 - 转发所有请求到对应的微服务"""
    logger.info(f"[Gateway] 收到HTTP请求: method={request.method}, path={path}")
    
    # 根据路径解析服务名
    service_name = route_service.get_service_name_from_path(path)
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"无法识别的服务路径: {path}"
        )
    
    # 获取服务实例
    instance = await route_service.get_service_instance(service_name)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"服务 {service_name} 暂时不可用"
        )
    
    # 构建目标URL
    target_url = f"http://{instance['ip']}:{instance['port']}/{path}"
    logger.info(f"[Gateway] 转发到: {target_url}")
    
    # 获取请求体
    body = await request.body()
    
    # 构建请求头
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-for"] = request.client.host if request.client else ""
    
    # 如果request.state中有user_id，添加到请求头
    if hasattr(request.state, "user_id") and request.state.user_id:
        headers["X-User-Id"] = request.state.user_id
        logger.info(f"[Gateway] 添加用户ID到请求头: X-User-Id={request.state.user_id}")
    
    # 转发请求
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 打印响应数据（调试用）
            try:
                response_json = response.json()
                response_str = json.dumps(response_json, ensure_ascii=False)
                if len(response_str) > 2000:
                    response_str = response_str[:2000] + "... [truncated]"
                logger.info(f"[Gateway] 响应数据: {response_str}")
            except:
                pass
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            logger.error(f"[Gateway] 上游服务响应超时: {target_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="上游服务响应超时"
            )
        except Exception as e:
            logger.error(f"[Gateway] 转发请求失败: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"网关内部错误: {str(e)}"
            )


# 注册到Nacos
@service_registry.register(
    service_name="gateway-service",
    port=4009,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4009)