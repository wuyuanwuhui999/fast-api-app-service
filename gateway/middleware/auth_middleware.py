import json
import logging
from typing import Optional, Set
from urllib.parse import parse_qs, urlparse

import jwt
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

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
    
    # WebSocket路径（特殊处理）
    WEBSOCKET_PATHS: Set[str] = {
        "/service/chat/ws/chat",
    }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        
        # 打印请求信息
        logger.info(f"[AuthMiddleware] 收到请求: method={request.method}, path={request.url.path}, full_url={request.url}")
        
        # 检查是否为WebSocket升级请求
        is_websocket = self._is_websocket_request(request)
        logger.info(f"[AuthMiddleware] is_websocket={is_websocket}")
        
        # 检查是否需要认证
        skip_auth = self.should_skip_auth(request.url.path)
        logger.info(f"[AuthMiddleware] skip_auth={skip_auth}")
        
        if skip_auth:
            logger.info(f"[AuthMiddleware] 跳过认证: {request.url.path}")
            return await call_next(request)
        
        # 获取token（WebSocket从URL参数获取，HTTP从Header获取）
        token = self.extract_token(request, is_websocket)
        logger.info(f"[AuthMiddleware] 提取到的token: {token[:50] if token else 'None'}...")
        
        if not token:
            logger.warning(f"[AuthMiddleware] 未提供认证令牌: path={request.url.path}")
            return self._unauthorized_response("未提供认证令牌", is_websocket)
        
        # 验证token并提取用户信息
        user_info = self.verify_token(token)
        logger.info(f"[AuthMiddleware] token验证结果: user_info={user_info}")
        
        if not user_info:
            logger.warning(f"[AuthMiddleware] 无效的认证令牌: path={request.url.path}")
            return self._unauthorized_response("无效的认证令牌", is_websocket)
        
        # 将用户ID存储到request.state中
        user_id = user_info.get("id")
        if user_id:
            request.state.user_id = user_id
            request.state.user_info = user_info
            logger.info(f"[AuthMiddleware] 用户认证成功: user_id={user_id}")
        
        # 对于WebSocket请求，将用户ID添加到URL参数中
        if is_websocket:
            # 修改请求的URL，添加X-User-Id参数
            original_url = str(request.url)
            logger.info(f"[AuthMiddleware] WebSocket原始URL: {original_url}")
            
            if "?" in original_url:
                new_url = f"{original_url}&X-User-Id={user_id}"
            else:
                new_url = f"{original_url}?X-User-Id={user_id}"
            
            logger.info(f"[AuthMiddleware] WebSocket修改后URL: {new_url}")
            
            # 使用内部属性修改请求URL（仅用于路由匹配）
            request._url = request.url.__class__(new_url)
        
        # 继续处理请求
        response = await call_next(request)
        return response
    
    def _is_websocket_request(self, request: Request) -> bool:
        """判断是否为WebSocket升级请求"""
        # 检查Upgrade头
        upgrade = request.headers.get("upgrade", "").lower()
        connection = request.headers.get("connection", "").lower()
        
        logger.debug(f"[AuthMiddleware] 检查WebSocket: upgrade={upgrade}, connection={connection}")
        
        if upgrade == "websocket" or "websocket" in connection:
            logger.info(f"[AuthMiddleware] 检测到WebSocket升级请求")
            return True
        
        # 检查路径是否为WebSocket端点
        path = request.url.path
        is_ws_path = path in self.WEBSOCKET_PATHS
        if is_ws_path:
            logger.info(f"[AuthMiddleware] 路径匹配WebSocket端点: {path}")
        return is_ws_path
    
    def should_skip_auth(self, path: str) -> bool:
        """判断是否需要跳过认证（精确匹配）"""
        return path in self.EXCLUDE_PATHS
    
    def extract_token(self, request: Request, is_websocket: bool = False) -> Optional[str]:
        """从请求中提取token"""
        
        # WebSocket请求：从URL参数获取
        if is_websocket:
            logger.info(f"[AuthMiddleware] WebSocket提取token, query_params={dict(request.query_params)}")
            
            # 解析URL参数
            query_params = request.query_params
            token = query_params.get("token")
            logger.info(f"[AuthMiddleware] 从query_params获取token: {token[:50] if token else 'None'}...")
            
            if token:
                # 移除Bearer前缀
                if token.startswith("Bearer "):
                    token = token[7:]
                    logger.info(f"[AuthMiddleware] 移除Bearer前缀后token: {token[:50]}...")
                return token
            
            # 尝试从原始URL解析
            raw_url = str(request.url)
            parsed = urlparse(raw_url)
            params = parse_qs(parsed.query)
            token_list = params.get("token", [])
            if token_list:
                token = token_list[0]
                if token.startswith("Bearer "):
                    token = token[7:]
                logger.info(f"[AuthMiddleware] 从parsed URL获取token: {token[:50]}...")
                return token
            
            logger.warning(f"[AuthMiddleware] WebSocket未找到token参数")
            return None
        
        # HTTP请求：从Authorization头获取
        auth_header = request.headers.get("Authorization")
        logger.info(f"[AuthMiddleware] HTTP Authorization头: {auth_header[:50] if auth_header else 'None'}...")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.info(f"[AuthMiddleware] 从Authorization头获取token: {token[:50]}...")
            return token
        
        # 从Cookie获取
        token = request.cookies.get("access_token")
        if token:
            logger.info(f"[AuthMiddleware] 从Cookie获取token: {token[:50]}...")
            return token
        
        # 从查询参数获取
        token = request.query_params.get("token")
        if token:
            logger.info(f"[AuthMiddleware] 从query_params获取token: {token[:50]}...")
            return token
        
        logger.warning(f"[AuthMiddleware] 未找到token")
        return None
    
    def verify_token(self, token: str) -> Optional[dict]:
        """验证token并返回用户信息"""
        try:
            logger.info(f"[AuthMiddleware] 开始验证token: {token[:50]}...")
            
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm],
                options={"verify_exp": True}
            )
            logger.info(f"[AuthMiddleware] token解码成功, payload keys: {list(payload.keys())}")
            
            # 解析sub字段
            sub = payload.get("sub")
            logger.info(f"[AuthMiddleware] sub字段类型: {type(sub)}, 值: {str(sub)[:100]}...")
            
            if sub:
                # sub可能是JSON字符串
                if isinstance(sub, str):
                    try:
                        user_info = json.loads(sub)
                        logger.info(f"[AuthMiddleware] sub解析为JSON成功, user_id={user_info.get('id')}")
                        return user_info
                    except json.JSONDecodeError as e:
                        logger.warning(f"[AuthMiddleware] sub不是有效的JSON: {str(e)}")
                        # 如果不是JSON，可能是直接的字符串
                        return {"id": sub, "userAccount": sub}
                elif isinstance(sub, dict):
                    logger.info(f"[AuthMiddleware] sub已经是dict, user_id={sub.get('id')}")
                    return sub
            
            logger.warning(f"[AuthMiddleware] sub字段为空或无效")
            return None
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"[AuthMiddleware] Token已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"[AuthMiddleware] 无效的Token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"[AuthMiddleware] Token验证异常: {str(e)}", exc_info=True)
            return None
    
    def _unauthorized_response(self, message: str, is_websocket: bool = False):
        """返回未授权响应"""
        logger.warning(f"[AuthMiddleware] 返回未授权响应: message={message}, is_websocket={is_websocket}")
        
        if is_websocket:
            # WebSocket返回HTTP 403，让客户端知道认证失败
            return Response(
                content=json.dumps({
                    "status": "FAIL",
                    "msg": message,
                    "data": None
                }),
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json"
            )
        
        return Response(
            content=json.dumps({
                "status": "FAIL",
                "msg": message,
                "data": None
            }),
            status_code=status.HTTP_401_UNAUTHORIZED,
            media_type="application/json"
        )