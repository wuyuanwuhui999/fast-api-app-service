# gateway/services/route_service.py
import random
import logging
from typing import Optional, Dict, Any, List
from common.utils.nacos_util import nacos_registry

logger = logging.getLogger(__name__)


class RouteService:
    """路由服务 - 服务发现和负载均衡"""
    
    # 路径到服务名的映射
    SERVICE_MAPPING = {
        "user": "user-service",
        "chat": "chat-service",
        "tenant": "tenant-service",
        "prompt": "prompt-service",
        "agent": "agent-service",
        "company": "company-service",  # 新增
    }

    # 服务实例缓存
    LOCAL_SERVICES = {
        "user-service": {"ip": "127.0.0.1", "port": 4005, "healthy": True, "weight": 1.0},
        "chat-service": {"ip": "127.0.0.1", "port": 4006, "healthy": True, "weight": 1.0},
        "tenant-service": {"ip": "127.0.0.1", "port": 4007, "healthy": True, "weight": 1.0},
        "prompt-service": {"ip": "127.0.0.1", "port": 4008, "healthy": True, "weight": 1.0},
        "agent-service": {"ip": "127.0.0.1", "port": 4010, "healthy": True, "weight": 1.0},
        "company-service": {"ip": "127.0.0.1", "port": 4011, "healthy": True, "weight": 1.0},  # 新增
    }
    
    def __init__(self):
        self.nacos = nacos_registry
    
    def get_service_name_from_path(self, path: str) -> Optional[str]:
        """
        根据请求路径解析服务名
        
        URL格式: /service/{模块名}/...
        例如: /service/user/getUserData -> user-service
        """
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "service":
            module_name = parts[1]
            return self.SERVICE_MAPPING.get(module_name)
        return None
    
    async def get_service_instance(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        获取服务实例（负载均衡）
        
        优先使用本地配置，如果Nacos可用则使用Nacos
        """
        # 方案1: 使用本地配置（稳定可靠）
        local_instance = self.LOCAL_SERVICES.get(service_name)
        if local_instance:
            logger.debug(f"使用本地配置的服务实例: {service_name} -> {local_instance['ip']}:{local_instance['port']}")
            # 验证本地服务是否可用
            if await self._check_service_health(local_instance['ip'], local_instance['port']):
                return local_instance.copy()
            else:
                logger.warning(f"本地服务实例不可用: {service_name} -> {local_instance['ip']}:{local_instance['port']}")
        
        # 方案2: 尝试从Nacos获取（如果本地配置不可用）
        instances = self.nacos.get_service_instances(service_name)
        
        if not instances:
            logger.warning(f"未找到服务实例: {service_name}")
            return None
        
        # 解析Nacos返回的实例数据
        parsed_instances = self._parse_nacos_instances(instances)
        
        if not parsed_instances:
            logger.warning(f"没有有效的服务实例: {service_name}")
            return None
        
        # 过滤健康的实例
        healthy_instances = [
            inst for inst in parsed_instances 
            if inst.get("healthy", True) and inst.get("ip") and inst.get("port")
        ]
        
        if not healthy_instances:
            logger.warning(f"服务 {service_name} 没有健康的实例")
            # 如果没有健康实例，返回第一个可用实例
            if parsed_instances:
                return parsed_instances[0]
            return None
        
        # 加权随机负载均衡
        return self._weighted_random_choice(healthy_instances)
    
    async def _check_service_health(self, ip: str, port: int) -> bool:
        """检查服务健康状态"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def _parse_nacos_instances(self, instances) -> List[Dict[str, Any]]:
        """解析Nacos返回的实例数据"""
        parsed_instances = []
        
        if isinstance(instances, dict):
            # 如果是字典，可能包含hosts字段
            if "hosts" in instances:
                for host in instances.get("hosts", []):
                    if isinstance(host, dict):
                        parsed_instances.append({
                            "ip": host.get("ip"),
                            "port": host.get("port"),
                            "healthy": host.get("healthy", True),
                            "weight": host.get("weight", 1.0)
                        })
            else:
                # 直接是实例字典
                parsed_instances.append({
                    "ip": instances.get("ip"),
                    "port": instances.get("port"),
                    "healthy": instances.get("healthy", True),
                    "weight": instances.get("weight", 1.0)
                })
        elif isinstance(instances, list):
            for inst in instances:
                if isinstance(inst, dict):
                    parsed_instances.append({
                        "ip": inst.get("ip"),
                        "port": inst.get("port"),
                        "healthy": inst.get("healthy", True),
                        "weight": inst.get("weight", 1.0)
                    })
                elif isinstance(inst, str) and ":" in inst:
                    parts = inst.split(":")
                    if len(parts) == 2:
                        parsed_instances.append({
                            "ip": parts[0],
                            "port": int(parts[1]),
                            "healthy": True,
                            "weight": 1.0
                        })
        
        return parsed_instances
    
    def _weighted_random_choice(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """加权随机选择实例"""
        weights = [inst.get("weight", 1.0) for inst in instances]
        total_weight = sum(weights)
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for inst, weight in zip(instances, weights):
            cumulative += weight
            if r <= cumulative:
                return {
                    "ip": inst.get("ip"),
                    "port": inst.get("port"),
                    "weight": weight,
                    "metadata": inst.get("metadata", {})
                }
        
        return {
            "ip": instances[0].get("ip"),
            "port": instances[0].get("port"),
            "weight": weights[0],
            "metadata": instances[0].get("metadata", {})
        }
    
    def refresh_cache(self):
        """刷新服务实例缓存"""
        pass