# common/utils/jwt_util.py
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt

# 直接从环境变量读取配置
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")


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

    # 生成 token
    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            leeway=timedelta(seconds=60)
        )
        return payload
    except jwt.PyJWTError as e:
        print(f"Token验证失败: {str(e)}")
        return None