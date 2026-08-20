import asyncio
import logging
from fastapi import Request
from common.config.common_database import SessionLocal
from user.repositories.login_log_repository import LoginLogRepository

logger = logging.getLogger(__name__)


def get_client_ip(request: Request) -> str:
    """获取客户端 IP（优先取网关透传的 X-Forwarded-For，取第一个）"""
    if request is None:
        return ""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return ""


def _write_login_log(user_id, ip, login_type):
    """同步写入登录日志（在后台线程执行）"""
    db = SessionLocal()
    try:
        LoginLogRepository(db).create(user_id, ip, login_type)
    except Exception as e:
        logger.error(f"写入登录日志失败: {str(e)}")
    finally:
        db.close()


def record_login_log(user_id, ip, login_type):
    """异步写入登录日志，不阻塞接口（线程池执行）"""
    try:
        asyncio.create_task(
            asyncio.to_thread(_write_login_log, user_id, ip, login_type)
        )
    except Exception as e:
        logger.error(f"提交登录日志任务失败: {str(e)}")
