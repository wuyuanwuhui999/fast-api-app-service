# common/utils/jwt_util.py
import os
import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt

# 直接从环境变量读取配置，增加默认值
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


def get_secret_key():
    """返回与 Spring Boot (jjwt) 一致的 HMAC 签名密钥。

    .env 中 SECRET_KEY 是 Base64 编码的 32 字节密钥字符串；
    Spring 侧 jjwt 会先 Base64 解码再作为 HMAC 密钥，这里保持一致，
    否则两项目用同一 SECRET_KEY 生成的 token 也无法相互验证。
    """
    raw = SECRET_KEY
    if not raw:
        raise ValueError("SECRET_KEY 未配置")
    try:
        return base64.b64decode(raw)
    except Exception as e:
        raise ValueError(f"SECRET_KEY 不是合法的 Base64 字符串: {e}")


def custom_json_serializer(obj: Any) -> str:
    """自定义 JSON 序列化器，处理 datetime 对象"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None,
        default_expire_days: int = 30
) -> str:
    """
    创建 JWT token，自动处理 JSON 序列化和有效期

    Args:
        data: 要编码的数据字典
        expires_delta: 自定义有效期时间差，如果不提供则使用 default_expire_days
        default_expire_days: 默认有效期天数（当 expires_delta 为 None 时使用）

    Returns:
        JWT token 字符串
    """
    # 序列化数据为 JSON 字符串
    to_encode = {
        k: json.dumps(v, default=custom_json_serializer, ensure_ascii=False)
        if isinstance(v, (dict, list)) else v
        for k, v in data.items()
    }

    # 设置有效期
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=default_expire_days)

    to_encode.update({"exp": expire})

    # 生成 token - 显式指定算法
    encoded_jwt = jwt.encode(
        to_encode,
        get_secret_key(),
        algorithm=ALGORITHM  # 使用 ALGORITHM 变量
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """验证 token，使用与创建相同的算法"""
    try:
        payload = jwt.decode(
            token,
            get_secret_key(),
            algorithms=[ALGORITHM],  # 使用与创建相同的算法列表
            leeway=timedelta(seconds=60)
        )
        return payload
    except jwt.PyJWTError as e:
        print(f"Token验证失败: {str(e)}")
        return None