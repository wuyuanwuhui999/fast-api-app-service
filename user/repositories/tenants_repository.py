import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from user.models.tenants_model import TenantUserModel, TenantModel, TenantUserRoleModel
from user.schemas.tenants_schema import TenantSchema, TenantCreateSchema, TenantUpdateSchema, TenantUserRoleSchema
from typing import List
from fastapi.logger import logger

class TenantsRepository:
    def __init__(self, db: Session):
        self.db = db

    async def get_user_tenants(self, user_id: str) -> List[TenantSchema]:
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
