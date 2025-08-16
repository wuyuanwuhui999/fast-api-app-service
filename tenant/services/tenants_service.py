from fastapi import Depends
from sqlalchemy.orm import Session

from common.schemas.user_schema import UserInDB
from tenant.repositories.tenants_repository import TenantsRepository
from tenant.schemas.tenants_schema import TenantUserRoleSchema, TenantUserRoleUpdateSchema, TenantUpdateSchema, \
    TenantCreateSchema
from common.config.common_database import get_db
from common.config.common_config import get_settings
import redis
from fastapi.logger import logger
from common.utils.result_util import ResultEntity, ResultUtil

settings = get_settings()


class TenantsService:
    def __init__(self, db: Session = Depends(get_db)):
        self.tenants_repository = TenantsRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)

    async def get_user_tenant_list(self, user_id: str) -> ResultEntity:
        """获取用户所属的所有租户"""
        try:
            tenants = await self.tenants_repository.get_user_tenant_list(user_id)
            if tenants:
                # 直接返回租户列表，不需要转换为 TenantUserSchema
                return ResultUtil.success(data=tenants, total=len(tenants))
            return ResultUtil.fail(msg="用户不属于任何租户")
        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取租户列表失败", data=None)

    async def get_tenant_user(self, user_id: str, tenant_id: str) -> ResultEntity:
        """获取用户在指定租户的信息"""
        try:
            tenant_user = await self.tenants_repository.get_tenant_user(user_id, tenant_id)
            if tenant_user:
                return ResultUtil.success(data=tenant_user)
            return ResultUtil.fail(msg="用户不在该租户中")
        except Exception as e:
            logger.error(f"获取当前租户的用户失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取当前租户的用户失败", data=None)

    async def create_tenant(self, tenant_data: TenantCreateSchema, current_user: UserInDB) -> ResultEntity:
        if not await self._check_admin_permission(current_user.id):
            return ResultUtil.fail(msg="无权创建租户")

        try:
            tenant = await self.tenants_repository.create_tenant(tenant_data, current_user.id)
            return ResultUtil.success(data=tenant)
        except Exception as e:
            logger.error(f"创建租户失败: {str(e)}")
            return ResultUtil.fail(msg="创建租户失败")

    async def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema,
                            current_user: UserInDB) -> ResultEntity:
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权修改此租户")

        success = await self.tenants_repository.update_tenant(tenant_id, update_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def delete_tenant(self, tenant_id: str, current_user: UserInDB) -> ResultEntity:
        if not await self._check_super_admin(current_user.id):
            return ResultUtil.fail(msg="需要超级管理员权限")

        success = await self.tenants_repository.delete_tenant(tenant_id)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def manage_tenant_user(
            self,
            tenant_id: str,
            user_id: str,
            role_data: TenantUserRoleUpdateSchema,
            current_user: UserInDB
    ) -> ResultEntity:
        # 权限检查
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权管理此租户用户")

        # 超级管理员才能设置管理员权限
        if role_data.role_type is not None and role_data.role_type >= 1:
            if not await self._check_super_admin(current_user.id):
                return ResultUtil.fail(msg="需要超级管理员权限设置管理员")

        # 更新用户角色
        full_data = TenantUserRoleSchema(
            tenant_id=tenant_id,
            user_id=user_id,
            **role_data.dict(exclude_unset=True)
        )

        success = await self.tenants_repository.set_tenant_user_role(full_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="操作失败")

    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否有管理员权限（至少是某个租户的管理员）"""
        try:
            # 获取用户的所有租户角色
            tenant_roles = await self.tenants_repository.get_user_tenants(user_id)
            # 检查是否有至少一个租户的角色是管理员(1)或超级管理员(2)
            return any(tenant.role_type >= 1 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_super_admin(self, user_id: str) -> bool:
        """检查用户是否是超级管理员（任意租户的角色为2）"""
        try:
            # 获取用户的所有租户角色
            tenant_roles = await self.tenants_repository.get_user_tenants(user_id)
            # 检查是否有任意租户的角色是超级管理员(2)
            return any(tenant.role_type == 2 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查超级管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_tenant_admin(self, tenant_id: str, user_id: str) -> bool:
        """检查用户是否是特定租户的管理员或超级管理员"""
        try:
            # 获取用户在该租户的角色
            tenant_roles = await self.tenants_repository.get_user_tenants(user_id)
            for tenant in tenant_roles:
                if tenant.id == tenant_id:
                    # 角色类型1(管理员)或2(超级管理员)都有权限
                    return tenant.role_type >= 1
            return False
        except Exception as e:
            logger.error(f"检查租户管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def get_tenant_users(
            self,
            tenant_id: str,
            current_user: UserInDB
    ) -> ResultEntity:
        """获取租户下的所有用户（需要租户管理员权限）"""
        try:
            # 权限检查 - 只有租户管理员或超级管理员可以查看
            if not await self._check_tenant_admin(tenant_id, current_user.id):
                return ResultUtil.error("无权查看此租户用户列表")

            # 获取租户用户列表
            users = await self.chat_repository.get_tenant_users(tenant_id)

            # 获取用户详细信息（从用户表）
            user_details = []
            for user_role in users:
                user = await self.tenants_repository.get_user(user_role.user_id)
                if user:
                    user_details.append({
                        **user_role.dict(),
                        "username": user.username,
                        "email": user.email,
                        "avatar": user.avatar
                    })

            return ResultUtil.success(data=user_details)

        except Exception as e:
            logger.error(f"获取租户用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.error("获取用户列表失败")