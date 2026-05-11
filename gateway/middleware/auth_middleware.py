from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import jwt
import json
import logging
from typing import Optional, Set

from common.config.common_config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthMiddleware(BaseHTTPMiddleware):
    """网关认证中间件 - 验证token并提取用户信息"""
    
    # 不需要认证的路径（精确匹配）
    EXCLUDE_PATHS: Set[str] = {
        "/health",
        # 用户模块不需要认证的接口
        "/service/user/register",
        "/service/user/login",
        "/service/user/sendEmailVertifyCode",
        "/service/user/resetPassword",
        "/service/user/loginByEmail",
        "/service/user/vertifyUser",
    }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 检查是否需要认证
        if self.should_skip_auth(request.url.path):
            return await call_next(request)
        
        # 获取token
        token = self.extract_token(request)
        
        if not token:
            return Response(
                content=json.dumps({
                    "status": "FAIL",
                    "msg": "未提供认证令牌",
                    "data": None
                }),
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # 验证token并提取用户信息
        user_info = self.verify_token(token)
        
        if not user_info:
            return Response(
                content=json.dumps({
                    "status": "FAIL",
                    "msg": "无效的认证令牌",
                    "data": None
                }),
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )
        
        # 将用户ID存储到request.state中，供后续路由使用
        user_id = user_info.get("id")
        if user_id:
            request.state.user_id = user_id
            request.state.user_info = user_info
        
        # 继续处理请求
        response = await call_next(request)
        return response
    
    def should_skip_auth(self, path: str) -> bool:
        """判断是否需要跳过认证（精确匹配）"""
        # 精确匹配白名单路径
        return path in self.EXCLUDE_PATHS
    
    def extract_token(self, request: Request) -> Optional[str]:
        """从请求中提取token"""
        # 从Authorization头获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]
        
        # 从Cookie获取
        token = request.cookies.get("access_token")
        if token:
            return token
        
        # 从查询参数获取
        token = request.query_params.get("token")
        if token:
            return token
        
        return None
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证token并返回用户信息"""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": True}
            )
            
            # 解析sub字段
            sub = payload.get("sub")
            if sub:
                # sub可能是JSON字符串
                if isinstance(sub, str):
                    try:
                        user_info = json.loads(sub)
                        return user_info
                    except json.JSONDecodeError:
                        # 如果不是JSON，可能是直接的字符串
                        return {"id": sub, "userAccount": sub}
                elif isinstance(sub, dict):
                    return sub
            
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的Token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Token验证异常: {str(e)}")
            return None