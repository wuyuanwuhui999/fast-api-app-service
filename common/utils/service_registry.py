# common/utils/service_registry.py
import os
import atexit
import signal
import logging
from functools import wraps
from typing import Optional

from common.utils.nacos_util import nacos_registry

logger = logging.getLogger(__name__)

# 直接从环境变量读取配置
ENABLE_NACOS = os.getenv("ENABLE_NACOS", "True").lower() == "true"


class ServiceRegistry:
    """服务注册管理器"""

    def __init__(self):
        self.registered_services = []

    def register(
            self,
            service_name: str,
            port: int,
            ip: str = "0.0.0.0",
            group: str = "DEFAULT_GROUP",
            weight: float = 1.0
    ):
        """注册服务装饰器"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 执行原函数启动app
                app = func(*args, **kwargs)

                # 获取实际IP（如果是0.0.0.0，使用localhost）
                actual_ip = ip
                if actual_ip == "0.0.0.0":
                    import socket
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        s.connect(("8.8.8.8", 80))
                        actual_ip = s.getsockname()[0]
                        s.close()
                    except:
                        actual_ip = "127.0.0.1"

                # 注册到Nacos
                if ENABLE_NACOS:
                    success = nacos_registry.register_service(
                        service_name=service_name,
                        ip=actual_ip,
                        port=port,
                        group=group,
                        weight=weight,
                        metadata={
                            "version": "1.0.0",
                            "protocol": "http"
                        }
                    )
                    if success:
                        self.registered_services.append({
                            "name": service_name,
                            "ip": actual_ip,
                            "port": port,
                            "group": group
                        })
                        logger.info(f"服务 {service_name} 已注册到Nacos")

                # 注册退出时的注销
                atexit.register(self._deregister_all)
                signal.signal(signal.SIGTERM, self._signal_handler)
                signal.signal(signal.SIGINT, self._signal_handler)

                return app

            return wrapper

        return decorator

    def _deregister_all(self):
        """注销所有已注册的服务"""
        for service in self.registered_services:
            nacos_registry.deregister_service(
                service_name=service["name"],
                ip=service["ip"],
                port=service["port"],
                group=service["group"]
            )

    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"收到信号 {signum}，正在注销服务...")
        self._deregister_all()
        import sys
        sys.exit(0)


# 全局服务注册管理器
service_registry = ServiceRegistry()