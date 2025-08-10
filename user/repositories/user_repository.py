import uuid
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from common.models.common_model import User
from user.models.user_model import TenantUserModel, TenantModel, TenantUserRoleModel
from user.schemas.user_schema import UserCreate, UserUpdate, TenantSchema, TenantCreateSchema, TenantUpdateSchema, \
    TenantUserRoleSchema
from typing import Optional, List
from fastapi.logger import logger

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, userId: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == userId).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def verify_user(self, user_account: str) -> int:
        """
            根据user_account精确查询用户数量
            :param user_account: 用户账号
            :return: 匹配该账号的用户数量
            """
        return (
            self.db.query(User)
                .filter(User.user_account == user_account)
                .count()
        )

    def get_user_by_user_account(self, user_account: str, password: str) -> Optional[User]:
        return (
            self.db.query(User)
                .filter(
                ((User.user_account == user_account) |
                 (User.email == user_account) |
                 (User.telephone == user_account)) &
                (User.password == password)
            )
                .first()
        )

    def get_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.db.query(User).offset(skip).limit(limit).all()

    def create_user(self, user: UserCreate) -> User:
        db_user = User(
            user_account=user.user_account,
            email=user.email,
            username=user.username,
            password=user.password,
            telephone=user.telephone,
            birthday=user.birthday,
            sex=user.sex,
            sign=user.sign,
            region=user.region,
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: str, user: UserUpdate) -> Optional[User]:
        db_user = self.get_user_by_id(user_id)
        if db_user:
            update_data = user.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def update_password(self, user_id: str, new_password: str) -> bool:
        db_user = self.get_user_by_id(user_id)
        if db_user:
            db_user.password = new_password
            self.db.commit()
            return True
        return False

    def verify_password(self, user_account: str, password: str) -> bool:
        return self.get_user_by_user_account(user_account, password)

    async def get_user_tenants(self, user_id: str) -> List[TenantSchema]:
        """获取用户所属的所有租户"""
        try:
            # 查询租户用户关联表获取用户所属租户ID列表
            tenant_users = self.db.query(TenantUserModel).filter(
                TenantUserModel.user_id == user_id
            ).all()

            if not tenant_users:
                return []

            # 获取租户详细信息
            tenant_ids = [tu.tenant_id for tu in tenant_users]
            tenants = self.db.query(TenantModel).filter(
                TenantModel.id.in_(tenant_ids)
            ).all()

            # 构建结果，包含用户在每个租户中的角色
            result = []
            for tenant in tenants:
                # 查找用户在该租户的角色
                role_type = next(
                    (tu.role_type for tu in tenant_users if tu.tenant_id == tenant.id),
                    0
                )

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
