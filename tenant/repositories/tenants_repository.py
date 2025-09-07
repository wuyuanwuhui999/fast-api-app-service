import uuid
from datetime import datetime

from sqlalchemy import select, delete, func
from sqlalchemy.orm import Session

from common.models.common_model import UserMode
from common.schemas.user_schema import UserSchema
from tenant.models.tenants_model import TenantUserModel, TenantModel, TenantUserRoleModel
from tenant.schemas.tenants_schema import TenantSchema, TenantCreateSchema, TenantUpdateSchema, TenantUserRoleSchema, TenantUserSchema
from typing import List, Optional, Any, Coroutine
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
            id=str(uuid.uuid4()).replace("-", ""),
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

    async def add_tenant_user(self, tenant_user: TenantUserSchema) -> TenantUserSchema:
        # 检查是否已存在相同的租户-用户关联
        existing = self.db.query(TenantUserModel).filter(
            TenantUserModel.tenant_id == tenant_user.tenant_id,
            TenantUserModel.user_id == tenant_user.user_id
        ).first()

        if existing:
            return None  # 已存在，不需要重复添加
        else:
            db_tenant_user = TenantUserModel(**tenant_user.model_dump())
            self.db.add(db_tenant_user)
            self.db.commit()
            # 刷新对象以获取数据库生成的字段（如果有的话）
            self.db.refresh(db_tenant_user)
            # 将数据库模型转换为 Schema 对象
            return TenantUserSchema.model_validate(db_tenant_user)
    
    async def get_user_by_id(self, user_id: str) -> Optional[type[UserSchema]]:
        return  self.db.query(UserMode).filter((UserMode.id == user_id) & (UserMode.disabled == 0)).first()

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

    async def get_user(self, user_id: str) -> Optional[UserMode]:
        """根据用户ID获取用户信息"""
        try:
            user = self.db.query(UserMode).filter(UserMode.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return None

    # 在 TenantsRepository 类中添加以下方法

    async def add_admin(self, tenant_id: str, user_id: str) -> bool:
        """设置用户为管理员"""
        try:
            # 查找用户的租户角色记录
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user:
                # 更新角色类型
                tenant_user.role_type = 1
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"设置管理员失败: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    async def delete_admin(self, tenant_id: str, user_id: str) -> bool:
        """取消用户的管理员权限（设置为普通用户）"""
        try:
            # 查找用户的租户角色记录
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user and tenant_user.role_type >= 1:  # 只有管理员或超级管理员才能被取消
                # 设置为普通用户
                tenant_user.role_type = 0
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"取消管理员权限失败: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    async def get_tenant_user_role(self, tenant_id: str, user_id: str) -> Optional[TenantUserSchema]:
        """获取用户在租户中的角色信息"""
        try:
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user:
                return TenantUserSchema.model_validate(tenant_user)
            return None
        except Exception as e:
            logger.error(f"获取租户用户角色失败: {str(e)}", exc_info=True)
            return None
