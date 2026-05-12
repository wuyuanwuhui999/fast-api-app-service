from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import httpx
from typing import Dict, Optional
import logging
from contextlib import asynccontextmanager

from gateway.middleware.auth_middleware import AuthMiddleware
from gateway.middleware.log_middleware import LogMiddleware  # 新增
from gateway.services.route_service import RouteService
from common.utils.service_registry import service_registry
from common.config.common_config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("Gateway服务启动中...")
    yield
    # 关闭时
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

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 初始化路由服务
route_service = RouteService()


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "gateway"}


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
    # 解析服务名
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
    
    # 获取请求体
    body = await request.body()
    
    # 准备请求头（移除host，添加x-forwarded头）
    headers = dict(request.headers)
    headers.pop("host", None)
    headers["x-forwarded-host"] = request.headers.get("host", "")
    headers["x-forwarded-proto"] = request.url.scheme
    headers["x-forwarded-for"] = request.client.host if request.client else ""
    
    # 获取用户ID（由认证中间件设置）
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        headers["X-User-Id"] = user_id
    
    # 创建客户端并转发请求
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params
            )
            
            # 返回响应
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            logger.error(f"请求超时: {target_url}")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="上游服务响应超时"
            )
        except httpx.ConnectError:
            logger.error(f"连接失败: {target_url}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="无法连接到上游服务"
            )
        except Exception as e:
            logger.error(f"转发请求失败: {str(e)}")
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