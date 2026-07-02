# common/utils/nacos_util.py
import os
import logging
from typing import Optional, Dict, Any

# 修改导入方式
try:
    # 尝试 3.x 版本的导入
    from nacos import NacosClient
except ImportError:
    # 尝试 2.x 版本的导入
    try:
        from nacos.client import NacosClient
    except ImportError:
        from nacos import NacosClient

logger = logging.getLogger(__name__)


class NacosServiceRegistry:
    """Nacos服务注册与发现工具类"""

    _instance = None
    _client: Optional[NacosClient] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            # 直接从环境变量读取Nacos配置
            self.nacos_host = os.getenv("NACOS_HOST")
            self.nacos_port = int(os.getenv("NACOS_PORT"))
            self.nacos_namespace = os.getenv("NACOS_NAMESPACE")
            self.nacos_username = os.getenv("NACOS_USERNAME")
            self.nacos_password = os.getenv("NACOS_PASSWORD")

            try:
                self._client = NacosClient(
                    server_addresses=f"{self.nacos_host}:{self.nacos_port}",
                    namespace=self.nacos_namespace,
                    username=self.nacos_username,
                    password=self.nacos_password
                )
                logger.info(f"Nacos客户端初始化完成: {self.nacos_host}:{self.nacos_port}")
            except Exception as e:
                logger.error(f"Nacos客户端初始化失败: {str(e)}")
                self._client = None

    @property
    def client(self) -> Optional[NacosClient]:
        return self._client

    def register_service(
            self,
            service_name: str,
            ip: str,
            port: int,
            group: str = "DEFAULT_GROUP",
            weight: float = 1.0,
            metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """注册服务到Nacos"""
        if not self._client:
            logger.warning("Nacos客户端未初始化，跳过服务注册")
            return False

        try:
            # 3.x 版本使用 add_naming_instance
            self._client.add_naming_instance(
                service_name=service_name,
                ip=ip,
                port=port,
                group_name=group,
                weight=weight,
                metadata=metadata or {}
            )
            logger.info(f"服务注册成功: {service_name}@{ip}:{port}")
            return True
        except AttributeError:
            try:
                # 尝试 2.x 版本的方法
                self._client.add_instance(
                    service_name=service_name,
                    ip=ip,
                    port=port,
                    group_name=group,
                    weight=weight,
                    metadata=metadata or {}
                )
                logger.info(f"服务注册成功: {service_name}@{ip}:{port}")
                return True
            except Exception as e:
                logger.error(f"服务注册失败: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"服务注册失败: {service_name}@{ip}:{port}, 错误: {str(e)}")
            return False

    def deregister_service(
            self,
            service_name: str,
            ip: str,
            port: int,
            group: str = "DEFAULT_GROUP"
    ) -> bool:
        """注销服务"""
        if not self._client:
            return False

        try:
            self._client.remove_naming_instance(
                service_name=service_name,
                ip=ip,
                port=port,
                group_name=group
            )
            logger.info(f"服务注销成功: {service_name}@{ip}:{port}")
            return True
        except AttributeError:
            try:
                self._client.remove_instance(
                    service_name=service_name,
                    ip=ip,
                    port=port,
                    group_name=group
                )
                logger.info(f"服务注销成功: {service_name}@{ip}:{port}")
                return True
            except Exception as e:
                logger.error(f"服务注销失败: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"服务注销失败: {service_name}@{ip}:{port}, 错误: {str(e)}")
            return False

    def get_service_instances(
            self,
            service_name: str,
            group: str = "DEFAULT_GROUP",
            healthy_only: bool = True
    ) -> list:
        """获取服务实例列表"""
        if not self._client:
            return []

        try:
            instances = self._client.list_naming_instance(
                service_name=service_name,
                group_name=group,
                healthy_only=healthy_only
            )
            return instances if instances else []
        except AttributeError:
            try:
                instances = self._client.list_instances(
                    service_name=service_name,
                    group_name=group,
                    healthy_only=healthy_only
                )
                return instances if instances else []
            except Exception as e:
                logger.error(f"获取服务实例失败: {str(e)}")
                return []
        except Exception as e:
            logger.error(f"获取服务实例失败: {service_name}, 错误: {str(e)}")
            return []


# 全局单例
nacos_registry = NacosServiceRegistry()