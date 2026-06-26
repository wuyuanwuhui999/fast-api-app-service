import uuid
from datetime import datetime
from typing import Optional  # <-- 新增这行导入

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from common.schemas.user_schema import UserSchema
from tenant.repositories.tenants_repository import TenantsRepository
from tenant.schemas.tenants_schema import TenantUpdateSchema, TenantCreateSchema, TenantUserSchema
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

    async def get_tenant_list(self, user_id: str, company_id: str = None) -> ResultEntity:
        """获取用户所属的所有租户，支持按企业ID筛选"""
        try:            
            tenants = self.tenants_repository.get_user_tenant_list(user_id, company_id)
            
            if tenants:                
                return ResultUtil.success(data=tenants, total=len(tenants))
            
            return ResultUtil.fail(msg="用户不属于任何租户", data=None)
            
        except Exception as e:
            logger.error(f"获取租户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取租户列表失败", data=None)

    async def get_tenant_user(self, user_id: str, tenant_id: str) -> ResultEntity:
        try:
            tenant_user_data = self.tenants_repository.get_tenant_user(user_id, tenant_id)
            if tenant_user_data:
                return ResultUtil.success(data=tenant_user_data)
            return ResultUtil.fail(msg="用户不在该租户中", data=None)
        except Exception as e:
            logger.error(f"获取当前租户的用户失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取当前租户的用户失败", data=None)

    async def get_tenant_users_with_pagination(
            self,
            tenant_id: str,
            page: int,
            page_size: int,
            keyword: Optional[str],
            current_user_id: str
    ) -> ResultEntity:
        """
        获取租户用户列表（分页），支持模糊搜索
        """
        try:
            if not await self._check_tenant_admin(tenant_id, current_user_id):
                return ResultUtil.fail(msg="无权查看此租户用户列表", data=None)

            # repository 返回包含用户信息的字典列表
            users_with_account, total = self.tenants_repository.get_tenant_users_with_pagination(
                tenant_id, page, page_size, keyword
            )

            return ResultUtil.success(data=users_with_account, total=total)

        except Exception as e:
            logger.error(f"获取租户用户分页列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取用户列表失败", data=None)

    async def create_tenant(self, tenant_data: TenantCreateSchema, current_user_id: str) -> ResultEntity:
        """创建租户，必须携带company_id"""
        if not await self._check_admin_permission(current_user_id):
            return ResultUtil.fail(msg="无权创建租户", data=None)

        # 验证company_id是否存在
        company = self.tenants_repository.get_company_by_id(tenant_data.company_id)
        if not company:
            return ResultUtil.fail(msg=f"公司不存在: {tenant_data.company_id}", data=None)

        try:
            tenant = self.tenants_repository.create_tenant(tenant_data, current_user_id)
            return ResultUtil.success(data=tenant)
        except ValueError as e:
            return ResultUtil.fail(msg=str(e), data=None)
        except Exception as e:
            logger.error(f"创建租户失败: {str(e)}")
            return ResultUtil.fail(msg="创建租户失败", data=None)

    async def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema,
                            user_id: str) -> ResultEntity:
        if not await self._check_tenant_admin(tenant_id, user_id):
            return ResultUtil.fail(msg="无权修改此租户", data=None)

        success = self.tenants_repository.update_tenant(tenant_id, update_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在", data=None)

    async def delete_tenant(self, tenant_id: str, user_id: str) -> ResultEntity:
        if not await self._check_super_admin(user_id):
            return ResultUtil.fail(msg="需要超级管理员权限", data=None)

        success = self.tenants_repository.delete_tenant(tenant_id)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在", data=None)

    async def add_tenant_user(
            self,
            tenant_id: str,
            user_id: str,
            current_user_id: str
    ) -> ResultEntity:
        if not await self._check_tenant_admin(tenant_id, current_user_id):
            return ResultUtil.fail(msg="无权添加此租户用户", data=None)

        user = self.tenants_repository.get_user_by_id(user_id)
        if user is None:
            return ResultUtil.fail(msg="该用户不存在", data=None)

        full_data = TenantUserSchema(
            id=str(uuid.uuid4()).replace("-", ""),
            role=0,
            join_date=datetime.now(),
            tenant_id=tenant_id,
            user_id=user_id,
            create_by=current_user_id,
            disabled=0
        )
        
        db_tenant_user = self.tenants_repository.add_tenant_user(full_data)

        if db_tenant_user is not None:
            return ResultUtil.success(data=1)
        else:
            return ResultUtil.fail(msg="该用户已存在", data=None)

    async def _check_admin_permission(self, user_id: str) -> bool:
        try:
            tenant_roles = self.tenants_repository.get_tenant_list(user_id)
            return any(tenant.role >= 1 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_super_admin(self, user_id: str) -> bool:
        try:
            tenant_roles = self.tenants_repository.get_tenant_list(user_id)
            return any(tenant.role == 2 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查超级管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_tenant_admin(self, tenant_id: str, user_id: str) -> bool:
        try:
            tenant_roles = self.tenants_repository.get_tenant_list(user_id)
            for tenant in tenant_roles:
                if tenant.tenant_id == tenant_id:
                    return tenant.role >= 1
            return False
        except Exception as e:
            logger.error(f"检查租户管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def get_tenant_users(
            self,
            tenant_id: str,
            user_id: str
    ) -> ResultEntity:
        try:
            if not await self._check_tenant_admin(tenant_id, user_id):
                return ResultUtil.fail(msg="无权查看此租户用户列表", data=None)

            users = self.tenants_repository.get_tenant_users(tenant_id)

            user_details = []
            for user_role in users:
                user = self.tenants_repository.get_user(user_role.user_id)
                if user:
                    user_details.append({
                        **user_role.dict(),
                        "username": user.username,
                        "email": user.email,
                        "avater": user.avater,
                        "user_account": user.user_account
                    })

            return ResultUtil.success(data=user_details)

        except Exception as e:
            logger.error(f"获取租户用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取用户列表失败", data=None)

    async def add_admin(self, tenant_id: str, current_user_id: str, user_id: str) -> ResultEntity:
        try:
            if not await self._check_super_admin(current_user_id):
                return ResultUtil.fail(msg="需要超级管理员权限", data=None)

            target_user = self.tenants_repository.get_user_by_id(user_id)
            if not target_user:
                return ResultUtil.fail(msg="目标用户不存在", data=None)

            tenant_user = self.tenants_repository.get_tenant_user_role(tenant_id, user_id)
            if not tenant_user:
                return ResultUtil.fail(msg="用户不在该租户中", data=None)

            success = self.tenants_repository.add_admin(tenant_id, user_id)

            if success:
                updated_user = self.tenants_repository.get_tenant_user_role(tenant_id, user_id)
                user_info = self.tenants_repository.get_user_by_id(user_id)

                return ResultUtil.success(data=1, msg="设置管理员成功")
            else:
                return ResultUtil.fail(msg="设置管理员失败", data=None)

        except Exception as e:
            logger.error(f"设置管理员失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="设置管理员失败", data=None)

    async def cancel_admin(self, tenant_id: str, current_user_id: str, user_id: str) -> ResultEntity:
        try:
            if not await self._check_super_admin(current_user_id):
                return ResultUtil.fail(msg="需要超级管理员权限", data=None)

            target_user = self.tenants_repository.get_user_by_id(user_id)
            if not target_user:
                return ResultUtil.fail(msg="目标用户不存在", data=None)

            tenant_user = self.tenants_repository.get_tenant_user_role(tenant_id, user_id)
            if not tenant_user:
                return ResultUtil.fail(msg="用户不在该租户中", data=None)

            if tenant_user.role == 0:
                return ResultUtil.fail(msg="用户不是管理员", data=None)

            success = self.tenants_repository.cancel_admin(tenant_id, user_id)

            if success:
                updated_user = self.tenants_repository.get_tenant_user_role(tenant_id, user_id)
                user_info = self.tenants_repository.get_user_by_id(user_id)

                return ResultUtil.success(data=1, msg="取消管理员权限成功")
            else:
                return ResultUtil.fail(msg="取消管理员权限失败", data=None)

        except Exception as e:
            logger.error(f"取消管理员权限失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="取消管理员权限失败", data=None)

    async def delete_tenant_user(
            self,
            tenant_id: str,
            user_id_to_delete: str,
            current_user_id: str
    ) -> ResultEntity:
        try:
            success = self.tenants_repository.delete_tenant_user(
                tenant_id, user_id_to_delete, current_user_id
            )

            if success:
                return ResultUtil.success(msg="用户删除成功", data=1)
            else:
                return ResultUtil.fail(msg="删除用户失败，请检查权限或用户状态", data=False)

        except Exception as e:
            logger.error(f"删除租户用户服务错误: {str(e)}")
            return ResultUtil.fail(msg=f"删除用户失败: {str(e)}", data=None)

    # ==================== 新增 search_users 方法 ====================
    
    async def search_tenant_users(
            self,
            company_id: str,
            tenant_id: str,
            keyword: Optional[str],
            page_num: int,
            page_size: int,
            current_user_id: str
    ) -> ResultEntity:
        """
        搜索用户列表（支持模糊搜索）
        查询该企业下的所有用户，并标记是否已在该租户中
        
        Args:
            company_id: 企业ID
            tenant_id: 租户ID
            keyword: 搜索关键词
            page_num: 页码
            page_size: 每页数量
            current_user_id: 当前用户ID
        """
        try:
            # 检查当前用户是否有权限查看该企业（企业管理员或租户管理员）
            # 这里简单检查：用户是否在企业中且角色 > 0
            from company.repositories.company_repository import CompanyRepository
            company_repo = CompanyRepository(self.tenants_repository.db)
            
            user_role_in_company = company_repo.get_user_role_in_company(company_id, current_user_id)
            if user_role_in_company < 1:
                return ResultUtil.fail(msg="无权查看该企业用户列表", data=None)

            # 执行搜索
            users, total = self.tenants_repository.search_tenant_users(
                company_id=company_id,
                tenant_id=tenant_id,
                keyword=keyword,
                page=page_num,
                page_size=page_size
            )

            return ResultUtil.success(data=users, total=total)

        except Exception as e:
            logger.error(f"搜索用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"搜索用户失败: {str(e)}", data=None)