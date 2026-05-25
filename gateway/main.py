# gateway/main.py - 完整修复版本
from fastapi import FastAPI, Request, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from typing import Dict, Optional
import logging
from contextlib import asynccontextmanager
import json
import jwt

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

# 添加日志中间件（最先执行，记录请求开始时间）
app.add_middleware(LogMiddleware)

# 初始化路由服务
route_service = RouteService()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}


def verify_token_and_get_user_id(token: str) -> Optional[str]:
    """验证token并返回用户ID"""
    try:
        logger.info(f"[WebSocketGateway] 开始验证token: {token[:50]}...")
        
        # 移除Bearer前缀
        if token.startswith("Bearer "):
            token = token[7:]
            logger.info(f"[WebSocketGateway] 移除Bearer前缀: {token[:50]}...")
        
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": True}
        )
        logger.info(f"[WebSocketGateway] token解码成功, payload keys: {list(payload.keys())}")
        
        # 解析sub字段
        sub = payload.get("sub")
        logger.info(f"[WebSocketGateway] sub字段类型: {type(sub)}")
        
        if sub:
            # sub可能是JSON字符串
            if isinstance(sub, str):
                try:
                    user_info = json.loads(sub)
                    user_id = user_info.get("id")
                    logger.info(f"[WebSocketGateway] 从JSON解析用户ID: {user_id}")
                    return user_id
                except json.JSONDecodeError as e:
                    logger.warning(f"[WebSocketGateway] sub不是有效的JSON: {str(e)}")
                    return sub
            elif isinstance(sub, dict):
                user_id = sub.get("id")
                logger.info(f"[WebSocketGateway] 从dict获取用户ID: {user_id}")
                return user_id
        
        logger.warning(f"[WebSocketGateway] 无法从token中提取用户ID")
        return None
        
    except jwt.ExpiredSignatureError:
        logger.warning(f"[WebSocketGateway] Token已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"[WebSocketGateway] 无效的Token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"[WebSocketGateway] Token验证异常: {str(e)}", exc_info=True)
        return None


@app.websocket("/service/chat/ws/chat")
async def websocket_gateway_chat(
    websocket: WebSocket,
    token: str = None,
):
    """
    Chat WebSocket网关 - 代理WebSocket连接到chat服务
    """
    logger.info(f"[ChatWebSocketGateway] ========== 收到WebSocket连接请求 ==========")
    logger.info(f"[ChatWebSocketGateway] token参数: {token[:100] if token else 'None'}...")
    
    if not token:
        logger.error(f"[ChatWebSocketGateway] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token")
        return
    
    user_id = verify_token_and_get_user_id(token)
    if not user_id:
        logger.error(f"[ChatWebSocketGateway] token验证失败")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    logger.info(f"[ChatWebSocketGateway] ✅ token验证成功，用户ID: {user_id}")
    
    service_name = "chat-service"
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[ChatWebSocketGateway] ❌ 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/chat/ws/chat?X-User-Id={user_id}"
    logger.info(f"[ChatWebSocketGateway] 目标WebSocket URL: {target_url}")
    
    try:
        await websocket.accept()
        logger.info(f"[ChatWebSocketGateway] ✅ 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[ChatWebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[ChatWebSocketGateway] ✅ 已连接到目标WebSocket服务")
        
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


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway(request: Request, path: str):
    """网关核心路由 - 转发所有请求到对应的微服务"""
    logger.info(f"[Gateway] 收到HTTP请求: method={request.method}, path={path}")
    
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
    
    # 对于HTTP请求，从Authorization头获取token并验证
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]
        user_id = verify_token_and_get_user_id(token)
        if user_id:
            headers["X-User-Id"] = user_id
            logger.info(f"[Gateway] 添加用户ID到请求头: X-User-Id={user_id}")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 打印响应数据
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