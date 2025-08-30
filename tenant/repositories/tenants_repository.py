import uuid
from datetime import datetime

from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from common.models.common_model import User
from tenant.models.tenants_model import TenantUserModel, TenantModel, TenantUserRoleModel
from tenant.schemas.tenants_schema import TenantSchema, TenantCreateSchema, TenantUpdateSchema, TenantUserRoleSchema, \
    TenantUserSchema
from typing import List, Optional
from fastapi.logger import logger


class TenantsRepository:
    def __init__(self, db: Session):
        self.db = db

    async def get_user_tenant_list(self, user_id: str) -> List[TenantSchema]:
        """获取用户所属的所有租户（优化版，单次查询）"""
        try:
            stmt = (
                select(TenantModel, TenantUserModel.role_type)
                    .join(
                    TenantUserModel,
                    TenantModel.id == TenantUserModel.tenant_id
                )
                    .where(TenantUserModel.user_id == user_id)
            )

            results = self.db.execute(stmt)

            result = []
            for tenant, role_type in results:
                tenant_schema = TenantSchema.model_validate(tenant)
                tenant_schema.role_type = role_type
                result.append(tenant_schema)

            return result

        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            raise

    async def get_tenant_user(self, user_id: str, tenant_id: str) -> Optional[TenantUserSchema]:
        """获取用户在指定租户的信息"""
        tenant_user = self.db.query(TenantUserModel).filter(
            (TenantUserModel.tenant_id == tenant_id) &
            (TenantUserModel.user_id == user_id)
        ).first()

        if tenant_user:
            return TenantUserSchema.model_validate(tenant_user)
        return None

    # 在 TenantsRepository 类中添加以下方法
    async def get_tenant_users_with_pagination(
            self,
            tenant_id: str,
            page: int = 1,
            page_size: int = 10
    ) -> tuple[List[TenantUserSchema], int]:
        """获取租户用户列表（分页）"""
        try:
            # 计算偏移量
            offset = (page - 1) * page_size

            # 查询总数
            total_stmt = select(func.count()).select_from(TenantUserModel).where(
                TenantUserModel.tenant_id == tenant_id
            )
            total = self.db.scalar(total_stmt)

            # 查询分页数据
            stmt = (
                select(TenantUserModel)
                    .where(TenantUserModel.tenant_id == tenant_id)
                    .order_by(TenantUserModel.join_date.desc())
                    .offset(offset)
                    .limit(page_size)
            )

            results = self.db.execute(stmt)
            users = [TenantUserSchema.model_validate(u) for u in results.scalars()]

            return users, total

        except Exception as e:
            logger.error(f"获取租户用户分页列表失败: {str(e)}", exc_info=True)
            raise

    async def create_tenant(self, tenant_data: TenantCreateSchema, creator_id: str) -> TenantSchema:
        db_tenant = TenantModel(
            id=str(uuid.uuid4()),
            name=tenant_data.name,
            code=tenant_data.code,
            description=tenant_data.description,
            created_by=creator_id,
            create_date=datetime.now()
        )
        self.db.add(db_tenant)
        await self.db.commit()
        return TenantSchema.model_validate(db_tenant)

    async def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema) -> bool:
        tenant = await self.db.get(TenantModel, tenant_id)
        if not tenant:
            return False

        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(tenant, field, value)

        tenant.update_date = datetime.now()
        await self.db.commit()
        return True

    async def delete_tenant(self, tenant_id: str) -> bool:
        result = await self.db.execute(
            delete(TenantModel).where(TenantModel.id == tenant_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def set_tenant_user_role(self, role_data: TenantUserRoleSchema) -> bool:
        # 添加或更新用户角色
        existing = await self.db.get(TenantUserRoleModel, (role_data.tenant_id, role_data.user_id))
        if existing:
            for field, value in role_data.dict(exclude_unset=True).items():
                setattr(existing, field, value)
        else:
            db_role = TenantUserRoleModel(**role_data.dict())
            self.db.add(db_role)

        await self.db.commit()
        return True

    async def get_tenant_users(self, tenant_id: str) -> List[TenantUserRoleSchema]:
        users = await self.db.execute(
            select(TenantUserRoleModel).where(TenantUserRoleModel.tenant_id == tenant_id)
        )
        return [TenantUserRoleSchema.model_validate(u) for u in users.scalars()]

    async def get_user_tenants(self, user_id: str) -> List[TenantUserSchema]:
        """获取用户的所有租户角色信息"""
        users = self.db.execute(
            select(TenantUserModel).where(
                (TenantUserModel.user_id == user_id) &
                (TenantUserModel.role_type > 0)  # 获取所有有管理权限的角色
            )
        )
        return [TenantUserSchema.model_validate(u) for u in users.scalars()]

        # 添加 get_user 方法

    async def get_user(self, user_id: str) -> Optional[User]:
        """根据用户ID获取用户信息"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return None