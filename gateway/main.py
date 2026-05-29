# gateway/main.py - 重构 WebSocket 公共代理逻辑
from fastapi import FastAPI, Request, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from typing import Optional, Callable, Awaitable
import logging
from contextlib import asynccontextmanager
import json
import asyncio

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


async def extract_user_id_from_token(token: str, service_name: str) -> Optional[str]:
    """
    从token中提取用户ID
    
    Args:
        token: JWT token字符串
        service_name: 服务名称，用于日志标识
    
    Returns:
        用户ID，如果提取失败则返回None
    """
    try:
        from common.utils.jwt_util import verify_token
        payload = verify_token(token)
        if not payload:
            logger.warning(f"[{service_name}] 无效的token")
            return None
        
        sub = payload.get("sub")
        user_id = None
        
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
            logger.warning(f"[{service_name}] 无法从token解析用户ID")
            return None
        
        logger.info(f"[{service_name}] 用户认证成功: user_id={user_id}")
        return user_id
        
    except Exception as e:
        logger.error(f"[{service_name}] token验证异常: {str(e)}")
        return None


async def websocket_proxy(
    websocket: WebSocket,
    token: Optional[str],
    service_name: str,
    target_path: str,
    gateway_name: str
) -> None:
    """
    通用的WebSocket代理方法
    
    Args:
        websocket: 客户端的WebSocket连接
        token: JWT token字符串
        service_name: 目标服务名称（如 "chat-service", "agent-service"）
        target_path: 目标服务的WebSocket路径
        gateway_name: 网关名称，用于日志标识（如 "ChatWebSocketGateway", "AgentWebSocketGateway"）
    """
    # 1. 验证token
    if not token:
        logger.warning(f"[{gateway_name}] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token parameter")
        return
    elif not token.startswith("Bearer "):
        await websocket.close(code=4001, reason="token格式错误，不是Bearer开头")
        return None    
    
    token = token[7:]

    user_id = await extract_user_id_from_token(token, gateway_name)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token or cannot extract user id")
        return
    
    # 2. 获取服务实例
    instance = await route_service.get_service_instance(service_name)
    if not instance:
        logger.error(f"[{gateway_name}] 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    # 3. 构建目标URL
    target_url = f"ws://{instance['ip']}:{instance['port']}{target_path}?X-User-Id={user_id}"
    logger.info(f"[{gateway_name}] 目标WebSocket URL: {target_url}")
    
    # 4. 接受客户端连接
    try:
        await websocket.accept()
        logger.info(f"[{gateway_name}] 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[{gateway_name}] 接受连接失败: {str(e)}")
        return
    
    # 5. 代理WebSocket通信
    import websockets as ws_lib
    
    target_websocket = None
    forward_to_target_task = None
    forward_to_client_task = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[{gateway_name}] 已连接到目标WebSocket服务")
        
        async def forward_to_target():
            """将客户端的消息转发到目标服务"""
            try:
                while True:
                    message = await websocket.receive_text()
                    await target_websocket.send(message)
            except WebSocketDisconnect:
                logger.info(f"[{gateway_name}] 客户端WebSocket连接断开（正常）")
            except Exception as e:
                # 检查是否是正常的关闭
                if "code = 1000" in str(e) or "sent 1000" in str(e):
                    logger.info(f"[{gateway_name}] WebSocket连接正常关闭")
                else:
                    logger.error(f"[{gateway_name}] 转发到目标服务失败: {str(e)}")
            finally:
                # 通知另一个任务结束
                if forward_to_client_task and not forward_to_client_task.done():
                    forward_to_client_task.cancel()
        
        async def forward_to_client():
            """将目标服务的消息转发到客户端"""
            try:
                while True:
                    message = await target_websocket.recv()
                    await websocket.send_text(message)
            except ws_lib.exceptions.ConnectionClosed as e:
                # WebSocket连接正常关闭
                logger.info(f"[{gateway_name}] 目标服务连接正常关闭: code={e.code}")
            except Exception as e:
                # 检查是否是正常的关闭
                if "code = 1000" in str(e) or "sent 1000" in str(e):
                    logger.info(f"[{gateway_name}] WebSocket连接正常关闭")
                else:
                    logger.error(f"[{gateway_name}] 转发到客户端失败: {str(e)}")
            finally:
                # 通知另一个任务结束
                if forward_to_target_task and not forward_to_target_task.done():
                    forward_to_target_task.cancel()
        
        # 创建两个转发任务
        forward_to_target_task = asyncio.create_task(forward_to_target())
        forward_to_client_task = asyncio.create_task(forward_to_client())
        
        # 等待任一任务完成（使用 wait 而不是 gather）
        done, pending = await asyncio.wait(
            [forward_to_target_task, forward_to_client_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"[{gateway_name}] WebSocket代理结束")
        
    except ws_lib.exceptions.WebSocketException as e:
        logger.error(f"[{gateway_name}] WebSocket连接错误: {str(e)}")
        try:
            await websocket.close(code=4002, reason=f"WebSocket connection error: {str(e)}")
        except:
            pass
    except Exception as e:
        logger.error(f"[{gateway_name}] WebSocket代理错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"WebSocket proxy error: {str(e)}")
        except:
            pass
    finally:
        if target_websocket:
            await target_websocket.close()
        logger.info(f"[{gateway_name}] WebSocket连接已关闭")


@app.websocket("/service/chat/ws/chat")
async def websocket_gateway_chat(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    Chat WebSocket网关 - 代理WebSocket连接到chat服务
    认证信息通过URL参数token传递
    """
    await websocket_proxy(
        websocket=websocket,
        token=token,
        service_name="chat-service",
        target_path="/service/chat/ws/chat",
        gateway_name="ChatWebSocketGateway"
    )


@app.websocket("/service/agent/ws/chat")
async def websocket_gateway_agent(
    websocket: WebSocket,
    token: Optional[str] = None,
):
    """
    Agent WebSocket网关 - 代理WebSocket连接到agent服务
    认证信息通过URL参数token传递
    """
    await websocket_proxy(
        websocket=websocket,
        token=token,
        service_name="agent-service",
        target_path="/service/agent/ws/chat",
        gateway_name="AgentWebSocketGateway"
    )


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