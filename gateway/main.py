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

# 注意：WebSocket不使用HTTP中间件，所以认证中间件对WebSocket无效
# 我们只在WebSocket路由中直接进行认证
# app.add_middleware(AuthMiddleware)  # 暂时注释，因为WebSocket不适用

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
async def websocket_gateway(
    websocket: WebSocket,
    token: str = None,
):
    """
    WebSocket网关 - 代理WebSocket连接到chat服务
    
    前端连接方式:
    ws://localhost:4009/service/chat/ws/chat?token=xxx
    
    网关会验证token，然后将用户ID通过X-User-Id参数传递给chat服务
    """
    
    logger.info(f"[WebSocketGateway] ========== 收到WebSocket连接请求 ==========")
    logger.info(f"[WebSocketGateway] token参数: {token[:100] if token else 'None'}...")
    logger.info(f"[WebSocketGateway] 所有查询参数: {dict(websocket.query_params)}")
    
    # 1. 验证token并获取用户ID
    if not token:
        logger.error(f"[WebSocketGateway] 未提供token参数")
        await websocket.close(code=4001, reason="Missing token")
        return
    
    user_id = verify_token_and_get_user_id(token)
    
    if not user_id:
        logger.error(f"[WebSocketGateway] token验证失败")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    logger.info(f"[WebSocketGateway] ✅ token验证成功，用户ID: {user_id}")
    
    # 2. 获取chat服务实例
    service_name = "chat-service"
    logger.info(f"[WebSocketGateway] 正在获取服务实例: {service_name}")
    
    instance = await route_service.get_service_instance(service_name)
    
    if not instance:
        logger.error(f"[WebSocketGateway] ❌ 服务不可用: {service_name}")
        await websocket.close(code=4003, reason=f"Service {service_name} unavailable")
        return
    
    logger.info(f"[WebSocketGateway] ✅ 获取到服务实例: {instance['ip']}:{instance['port']}")
    
    # 3. 构建目标WebSocket URL（带上X-User-Id参数）
    target_url = f"ws://{instance['ip']}:{instance['port']}/service/chat/ws/chat?X-User-Id={user_id}"
    logger.info(f"[WebSocketGateway] 目标WebSocket URL: {target_url}")
    
    # 4. 接受客户端WebSocket连接
    try:
        await websocket.accept()
        logger.info(f"[WebSocketGateway] ✅ 已接受客户端WebSocket连接")
    except Exception as e:
        logger.error(f"[WebSocketGateway] 接受连接失败: {str(e)}")
        return
    
    # 5. 创建到目标服务的WebSocket连接并转发消息
    import asyncio
    import websockets as ws_lib
    
    target_websocket = None
    
    try:
        # 连接到目标WebSocket服务
        logger.info(f"[WebSocketGateway] 正在连接到目标服务...")
        target_websocket = await ws_lib.connect(target_url)
        logger.info(f"[WebSocketGateway] ✅ 已连接到目标WebSocket服务")
        
        # 双向消息转发
        async def forward_to_target():
            """将客户端的消息转发到目标服务"""
            try:
                while True:
                    # 接收客户端消息
                    message = await websocket.receive_text()
                    logger.debug(f"[WebSocketGateway] 客户端 -> 目标: {message[:100]}...")
                    # 转发到目标服务
                    await target_websocket.send(message)
            except WebSocketDisconnect:
                logger.info(f"[WebSocketGateway] 客户端WebSocket连接断开")
            except Exception as e:
                logger.error(f"[WebSocketGateway] 转发到目标服务失败: {str(e)}")
            finally:
                if target_websocket:
                    await target_websocket.close()
        
        async def forward_to_client():
            """将目标服务的消息转发到客户端"""
            try:
                while True:
                    # 接收目标服务消息
                    message = await target_websocket.recv()
                    logger.debug(f"[WebSocketGateway] 目标 -> 客户端: {message[:100]}...")
                    # 转发到客户端
                    await websocket.send_text(message)
            except Exception as e:
                logger.error(f"[WebSocketGateway] 转发到客户端失败: {str(e)}")
        
        # 并发执行转发任务
        await asyncio.gather(
            forward_to_target(),
            forward_to_client(),
            return_exceptions=True
        )
        
    except ws_lib.exceptions.WebSocketException as e:
        logger.error(f"[WebSocketGateway] WebSocket连接错误: {str(e)}")
        try:
            await websocket.close(code=4002, reason=f"WebSocket connection error: {str(e)}")
        except:
            pass
    except Exception as e:
        logger.error(f"[WebSocketGateway] WebSocket代理错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"WebSocket proxy error: {str(e)}")
        except:
            pass
    finally:
        if target_websocket:
            await target_websocket.close()
        logger.info(f"[WebSocketGateway] WebSocket连接已关闭")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def gateway(request: Request, path: str):
    """
    网关核心路由 - 转发所有请求到对应的微服务
    
    路由规则：
    - /service/user/* -> user-service
    - /service/chat/* -> chat-service  
    - /service/tenant/* -> tenant-service
    - /service/prompt/* -> prompt-service
    """
    logger.info(f"[Gateway] 收到HTTP请求: method={request.method}, path={path}, full_url={request.url}")
    
    # 解析服务名
    service_name = route_service.get_service_name_from_path(path)
    logger.info(f"[Gateway] 解析服务名: {service_name}")
    
    if not service_name:
        logger.warning(f"[Gateway] 无法识别的服务路径: {path}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"无法识别的服务路径: {path}"
        )
    
    # 获取服务实例
    instance = await route_service.get_service_instance(service_name)
    logger.info(f"[Gateway] 获取服务实例: {instance}")
    
    if not instance:
        logger.error(f"[Gateway] 服务不可用: {service_name}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"服务 {service_name} 暂时不可用"
        )
    
    # 构建目标URL
    target_url = f"http://{instance['ip']}:{instance['port']}/{path}"
    logger.info(f"[Gateway] 目标URL: {target_url}")
    
    # 获取请求体
    body = await request.body()
    
    # 准备请求头
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
    
    # 创建客户端并转发请求
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            logger.info(f"[Gateway] 转发请求: {request.method} {target_url}")
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            logger.info(f"[Gateway] 收到响应: status_code={response.status_code}")
            
            # 返回响应
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            logger.error(f"[Gateway] 请求超时: {target_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="上游服务响应超时"
            )
        except httpx.ConnectError:
            logger.error(f"[Gateway] 连接失败: {target_url}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="无法连接到上游服务"
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