import uuid
from datetime import datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from common.schemas.user_schema import UserSchema
from tenant.repositories.tenants_repository import TenantsRepository
from tenant.schemas.tenants_schema import  TenantUpdateSchema, TenantCreateSchema, TenantUserSchema
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

    # 在 TenantsService 类中添加以下方法
    async def get_tenant_users_with_pagination(
            self,
            tenant_id: str,
            page: int,
            page_size: int,
            current_user: UserSchema
    ) -> ResultEntity:
        """获取租户用户列表（分页）"""
        try:
            # 权限检查 - 只有租户管理员或超级管理员可以查看
            if not await self._check_tenant_admin(tenant_id, current_user.id):
                return ResultUtil.fail("无权查看此租户用户列表")

            # 获取租户用户分页列表
            users, total = await self.tenants_repository.get_tenant_users_with_pagination(
                tenant_id, page, page_size
            )

            # 获取用户详细信息（从用户表）
            user_details = []
            for tenant_user in users:
                user = await self.tenants_repository.get_user(tenant_user.user_id)
                if user:
                    user_details.append({
                        "id": tenant_user.id,
                        "tenant_id": tenant_user.tenant_id,
                        "user_id": tenant_user.user_id,
                        "role_type": tenant_user.role_type,
                        "disabled": tenant_user.disabled,
                        "join_date": tenant_user.join_date,
                        "username": user.username,
                        "email": user.email,
                        "avater": user.avater
                    })

            return ResultUtil.success(data=user_details, total=total)

        except Exception as e:
            logger.error(f"获取租户用户分页列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail("获取用户列表失败")

    async def create_tenant(self, tenant_data: TenantCreateSchema, current_user: UserSchema) -> ResultEntity:
        if not await self._check_admin_permission(current_user.id):
            return ResultUtil.fail(msg="无权创建租户")

        try:
            tenant = await self.tenants_repository.create_tenant(tenant_data, current_user.id)
            return ResultUtil.success(data=tenant)
        except Exception as e:
            logger.error(f"创建租户失败: {str(e)}")
            return ResultUtil.fail(msg="创建租户失败")

    async def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema,
                            current_user: UserSchema) -> ResultEntity:
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权修改此租户")

        success = await self.tenants_repository.update_tenant(tenant_id, update_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def delete_tenant(self, tenant_id: str, current_user: UserSchema) -> ResultEntity:
        if not await self._check_super_admin(current_user.id):
            return ResultUtil.fail(msg="需要超级管理员权限")

        success = await self.tenants_repository.delete_tenant(tenant_id)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def add_tenant_user(
            self,
            tenant_id: str,
            user_id: str,
            current_user: UserSchema
    ) -> ResultEntity:
        # 权限检查
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权添加此租户用户")

        user = await self.tenants_repository.get_user_by_id(user_id)
        if user is None:
            return ResultUtil.fail(msg="该用户不存在")

        # 更新用户角色
        full_data = TenantUserSchema(
            id=str(uuid.uuid4()).replace("-", ""),
            role_type=0,
            join_date=datetime.now(),
            tenant_id=tenant_id,
            user_id=user_id,
            create_by=current_user.id,
            disabled=0
        )
        
        db_tenant_user = await self.tenants_repository.add_tenant_user(full_data)

        if db_tenant_user is not None:
            return ResultUtil.success(data={
                **db_tenant_user.model_dump(),
                "username": user.username,
                "email": user.email,
                "avater": user.avater
            })
        else:
            return ResultUtil.fail(msg="该用户已存在")

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
                if tenant.tenant_id == tenant_id:  # 注意：这里应该是 tenant.tenant_id 而不是 tenant.id
                    # 角色类型1(管理员)或2(超级管理员)都有权限
                    return tenant.role_type >= 1
            return False
        except Exception as e:
            logger.error(f"检查租户管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def get_tenant_users(
            self,
            tenant_id: str,
            current_user: UserSchema
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
                        "avater": user.avater
                    })

            return ResultUtil.success(data=user_details)

        except Exception as e:
            logger.error(f"获取租户用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.error("获取用户列表失败")