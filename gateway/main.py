# gateway/main.py - 修改 WebSocket token 从 URL 参数获取
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
    logger.info("Gateway服务启动中...")
    yield
    logger.info("Gateway服务关闭...")


app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuthMiddleware)
app.add_middleware(LogMiddleware)

route_service = RouteService()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "gateway"}


@app.websocket("/service/chat/ws/chat")
async def websocket_gateway_chat(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    Chat WebSocket网关 - 代理WebSocket连接到chat服务
    认证信息通过URL参数token传递
    """
    user_id = None
    
    if not token:
        logger.warning(f"[ChatWebSocketGateway] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token parameter")
        return
    
    try:
        from common.utils.jwt_util import verify_token
        payload = verify_token(token)
        if not payload:
            logger.warning(f"[ChatWebSocketGateway] 无效的token")
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        sub = payload.get("sub")
        if sub:
            if isinstance(sub, str):
                try:
                    user_info = json.loads(sub)
                    user_id = user_info.get("id")
                except json.JSONDecodeError:
                    user_id = sub
            elif isinstance(sub, dict):
                user_id = sub.get("id")
        
        if not user_id:
            logger.warning(f"[ChatWebSocketGateway] 无法从token解析用户ID")
            await websocket.close(code=4001, reason="Cannot extract user id from token")
            return
        
        logger.info(f"[ChatWebSocketGateway] 用户认证成功: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"[ChatWebSocketGateway] token验证异常: {str(e)}")
        await websocket.close(code=4001, reason=f"Token verification failed: {str(e)}")
        return
    
    service_name = "chat-service"
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[ChatWebSocketGateway] 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/chat/ws/chat?X-User-Id={user_id}"
    logger.info(f"[ChatWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    try:
        await websocket.accept()
        logger.info(f"[ChatWebSocketGateway] 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[ChatWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[ChatWebSocketGateway] 已连接到目标WebSocket服务")
        
        async def forward_to_target():
            try:
                while True:
                    message = await websocket.receive_text()
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
    token: Optional[str] = None,
):
    """
    Agent WebSocket网关 - 代理WebSocket连接到agent服务
    认证信息通过URL参数token传递
    """
    user_id = None
    
    if not token:
        logger.warning(f"[AgentWebSocketGateway] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token parameter")
        return
    
    try:
        from common.utils.jwt_util import verify_token
        payload = verify_token(token)
        if not payload:
            logger.warning(f"[AgentWebSocketGateway] 无效的token")
            await websocket.close(code=4001, reason="Invalid token")
            return
        
        sub = payload.get("sub")
        if sub:
            if isinstance(sub, str):
                try:
                    user_info = json.loads(sub)
                    user_id = user_info.get("id")
                except json.JSONDecodeError:
                    user_id = sub
            elif isinstance(sub, dict):
                user_id = sub.get("id")
        
        if not user_id:
            logger.warning(f"[AgentWebSocketGateway] 无法从token解析用户ID")
            await websocket.close(code=4001, reason="Cannot extract user id from token")
            return
        
        logger.info(f"[AgentWebSocketGateway] 用户认证成功: user_id={user_id}")
        
    except Exception as e:
        logger.error(f"[AgentWebSocketGateway] token验证异常: {str(e)}")
        await websocket.close(code=4001, reason=f"Token verification failed: {str(e)}")
        return
    
    service_name = "agent-service"
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[AgentWebSocketGateway] 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/agent/ws/chat?X-User-Id={user_id}"
    logger.info(f"[AgentWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    try:
        await websocket.accept()
        logger.info(f"[AgentWebSocketGateway] 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[AgentWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[AgentWebSocketGateway] 已连接到目标WebSocket服务")
        
        async def forward_to_target():
            try:
                while True:
                    message = await websocket.receive_text()
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
    service_name = route_service.get_service_name_from_path(path)
    if not service_name:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"无法识别的服务路径: {path}"
        )
    
    instance = await route_service.get_service_instance(service_name)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"服务 {service_name} 暂时不可用"
        )
    
    target_url = f"http://{instance['ip']}:{instance['port']}/{path}"
    
    body = await request.body()
    
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-for"] = request.client.host if request.client else ""
    
    if hasattr(request.state, "user_id") and request.state.user_id:
        headers["X-User-Id"] = request.state.user_id
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="上游服务响应超时"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"网关内部错误: {str(e)}"
            )


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