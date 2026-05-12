import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

from gateway.services.log_service import log_service

logger = logging.getLogger(__name__)


class LogMiddleware(BaseHTTPMiddleware):
    """网关日志中间件 - 记录所有请求响应"""
    
    # 不需要记录日志的路径
    EXCLUDE_PATHS = {
        "/health",
        "/metrics",
        "/favicon.ico",
    }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并记录日志"""
        
        # 检查是否需要跳过日志
        if request.url.path in self.EXCLUDE_PATHS:
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取用户ID（可能已经由AuthMiddleware设置）
        user_id = getattr(request.state, "user_id", None)
        
        error_message = None
        response = None
        
        try:
            # 执行请求
            response = await call_next(request)
            return response
            
        except Exception as e:
            error_message = str(e)
            raise
            
        finally:
            # 计算执行时间
            execute_time = int((time.time() - start_time) * 1000)
            
            # 异步保存日志（如果响应存在）
            if response is not None:
                # 使用asyncio.create_task异步保存，不阻塞响应
                import asyncio
                asyncio.create_task(
                    log_service.save_request_log(
                        request=request,
                        response=response,
                        user_id=user_id,
                        execute_time=execute_time,
                        error_message=error_message
                    )
                )