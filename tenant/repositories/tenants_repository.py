import uuid
from datetime import datetime

from sqlalchemy import select, delete, func, or_, and_
from sqlalchemy.orm import Session, joinedload

from common.models.common_model import UserMode
from common.schemas.user_schema import UserSchema
from tenant.models.tenants_model import TenantUserModel, TenantModel, TenantUserRoleModel
from tenant.schemas.tenants_schema import TenantSchema, TenantCreateSchema, TenantUpdateSchema, TenantUserRoleSchema, TenantUserSchema
from typing import List, Optional, Any, Coroutine, Dict
from fastapi.logger import logger


class TenantsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_tenant_list(self, user_id: str, company_id: Optional[str] = None) -> List[TenantSchema]:
        """获取用户所属的所有租户（包括公开租户）- 同步方法，支持company_id筛选"""
        try:
            from sqlalchemy import or_
            
            # 构建查询条件
            conditions = or_(
                TenantUserModel.user_id == user_id,  # 用户直接所属的租户
                TenantModel.code == 'public'         # 公开租户
            )
            
            stmt = (
                select(TenantModel, TenantUserModel.role_type)
                .outerjoin(
                    TenantUserModel,
                    TenantModel.id == TenantUserModel.tenant_id
                )
                .where(conditions)
                .distinct()
            )
            
            # 如果指定了company_id，添加筛选条件
            if company_id:
                stmt = stmt.where(TenantModel.company_id == company_id)

            results = self.db.execute(stmt)
            
            result = []
            for idx, (tenant, role_type) in enumerate(results):
                tenant_schema = TenantSchema.model_validate(tenant)
                tenant_schema.role_type = role_type if role_type is not None else 0
                result.append(tenant_schema)

            return result

        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            raise

    def get_tenant_user(self, user_id: str, tenant_id: str) -> Optional[Dict]:
        """获取用户在指定租户的信息，并关联查询租户名称"""
        try:
            result = (
                self.db.query(TenantUserModel, TenantModel.name.label('tenant_name'))
                .join(TenantModel, TenantModel.id == TenantUserModel.tenant_id)
                .filter(
                    TenantUserModel.tenant_id == tenant_id,
                    TenantUserModel.user_id == user_id
                )
                .first()
            )
            
            if result:
                tenant_user, tenant_name = result
                tenant_user_dict = {
                    'id': tenant_user.id,
                    'tenant_id': tenant_user.tenant_id,
                    'user_id': tenant_user.user_id,
                    'role_type': tenant_user.role_type,
                    'join_date': tenant_user.join_date,
                    'create_by': tenant_user.create_by,
                    'disabled': tenant_user.disabled,
                    'tenant_name': tenant_name
                }
                return tenant_user_dict
            return None
            
        except Exception as e:
            logger.error(f"获取租户用户信息失败: {str(e)}", exc_info=True)
            raise

    def get_tenant_users_with_pagination(
            self,
            tenant_id: str,
            page: int = 1,
            page_size: int = 10
    ) -> tuple[List[TenantUserSchema], int]:
        """获取租户用户列表（分页）- 同步方法"""
        try:
            offset = (page - 1) * page_size

            total_stmt = select(func.count()).select_from(TenantUserModel).where(
                TenantUserModel.tenant_id == tenant_id
            )
            total = self.db.scalar(total_stmt)

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

    def get_company_by_id(self, company_id: str) -> Optional[Any]:
        """根据公司ID查询公司是否存在"""
        try:
            from company.models.company_model import CompanyModel
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            return company
        except Exception as e:
            logger.error(f"查询公司失败: {str(e)}")
            return None

    def create_tenant(self, tenant_data: TenantCreateSchema, creator_id: str) -> TenantSchema:
        """创建租户，需要验证company_id是否存在"""
        # 验证公司是否存在
        company = self.get_company_by_id(tenant_data.company_id)
        if not company:
            raise ValueError(f"公司不存在: {tenant_data.company_id}")
        
        db_tenant = TenantModel(
            id=str(uuid.uuid4()).replace("-", ""),
            company_id=tenant_data.company_id,
            name=tenant_data.name,
            code=tenant_data.code,
            description=tenant_data.description,
            created_by=creator_id,
            create_date=datetime.now()
        )
        self.db.add(db_tenant)
        self.db.commit()
        self.db.refresh(db_tenant)
        return TenantSchema.model_validate(db_tenant)

    def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema) -> bool:
        tenant = self.db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        if not tenant:
            return False

        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(tenant, field, value)

        tenant.update_date = datetime.now()
        self.db.commit()
        return True

    def delete_tenant(self, tenant_id: str) -> bool:
        result = self.db.execute(
            delete(TenantModel).where(TenantModel.id == tenant_id)
        )
        self.db.commit()
        return result.rowcount > 0

    def add_tenant_user(self, tenant_user: TenantUserSchema) -> TenantUserSchema:
        existing = self.db.query(TenantUserModel).filter(
            TenantUserModel.tenant_id == tenant_user.tenant_id,
            TenantUserModel.user_id == tenant_user.user_id
        ).first()

        if existing:
            return None
        else:
            db_tenant_user = TenantUserModel(**tenant_user.model_dump(exclude={'tenant_name'}))
            self.db.add(db_tenant_user)
            self.db.commit()
            self.db.refresh(db_tenant_user)
            return TenantUserSchema.model_validate(db_tenant_user)
    
    def get_user_by_id(self, user_id: str) -> Optional[UserMode]:
        return self.db.query(UserMode).filter((UserMode.id == user_id) & (UserMode.disabled == 0)).first()

    def get_tenant_users(self, tenant_id: str) -> List[TenantUserRoleSchema]:
        users = self.db.execute(
            select(TenantUserRoleModel).where(TenantUserRoleModel.tenant_id == tenant_id)
        )
        return [TenantUserRoleSchema.model_validate(u) for u in users.scalars()]

    def get_tenant_list(self, user_id: str) -> List[TenantUserSchema]:
        users = self.db.execute(
            select(TenantUserModel).where(
                (TenantUserModel.user_id == user_id) &
                (TenantUserModel.role_type > 0)
            )
        )
        return [TenantUserSchema.model_validate(u) for u in users.scalars()]

    def get_user(self, user_id: str) -> Optional[UserMode]:
        try:
            user = self.db.query(UserMode).filter(UserMode.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return None

    def add_admin(self, tenant_id: str, user_id: str) -> bool:
        try:
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user:
                tenant_user.role_type = 1
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"设置管理员失败: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    def delete_admin(self, tenant_id: str, user_id: str) -> bool:
        try:
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user and tenant_user.role_type >= 1:
                tenant_user.role_type = 0
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"取消管理员权限失败: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    def get_tenant_user_role(self, tenant_id: str, user_id: str) -> Optional[TenantUserSchema]:
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

    def delete_tenant_user(
            self,
            tenant_id: str,
            user_id_to_delete: str,
            current_user_id: str
    ) -> bool:
        try:
            from user.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.db)

            current_user = user_repo.get_user_by_id(current_user_id)
            if not current_user or current_user.disabled == 1:
                return False

            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == current_user_id,
                TenantUserModel.role_type > 1
            ).first()

            if not tenant_user:
                return False

            delete_result = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id_to_delete
            ).delete()

            self.db.commit()
            return delete_result > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除租户用户失败: {str(e)}")
            return False