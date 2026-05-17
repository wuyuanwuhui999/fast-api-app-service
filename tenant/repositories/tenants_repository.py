import uuid
from datetime import datetime

from sqlalchemy import select, delete, func, or_
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

    def get_user_tenant_list(self, user_id: str) -> List[TenantSchema]:
        """获取用户所属的所有租户（包括公开租户）- 同步方法"""
        try:
            from sqlalchemy import or_
            
            stmt = (
                select(TenantModel, TenantUserModel.role_type)
                    .outerjoin(  # 使用 outerjoin 以包含没有关联的公开租户
                    TenantUserModel,
                    TenantModel.id == TenantUserModel.tenant_id
                )
                    .where(
                    or_(
                        TenantUserModel.user_id == user_id,  # 用户直接所属的租户
                        TenantModel.code == 'public'         # 公开租户
                    )
                )
                    .distinct()  # 去重，避免重复返回相同租户
            )

            results = self.db.execute(stmt)
            
            # ========== 打印原始查询结果 ==========
            logger.info(f"[get_user_tenant_list] 用户ID: {user_id}")
            
            result = []
            for idx, (tenant, role_type) in enumerate(results):
                logger.info(f"[get_user_tenant_list] 结果 {idx + 1}:")
                logger.info(f"  - 租户ID: {tenant.id}")
                logger.info(f"  - 租户名称: {tenant.name}")
                logger.info(f"  - 租户编码: {tenant.code}")
                logger.info(f"  - 租户描述: {tenant.description}")
                logger.info(f"  - 租户状态: {tenant.status}")
                logger.info(f"  - 角色类型: {role_type}")
                
                tenant_schema = TenantSchema.model_validate(tenant)
                # 对于公开租户，如果没有关联记录，role_type 可能为 None
                tenant_schema.role_type = role_type if role_type is not None else 0
                result.append(tenant_schema)
            
            # 打印最终返回的数据
            logger.info(f"[get_user_tenant_list] 最终返回租户数量: {len(result)}")
            for idx, tenant in enumerate(result):
                logger.info(f"[get_user_tenant_list] 返回数据 {idx + 1}: id={tenant.id}, name={tenant.name}, code={tenant.code}, role_type={tenant.role_type}")
            # ========== 打印结束 ==========

            return result

        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            raise

    def get_tenant_user(self, user_id: str, tenant_id: str) -> Optional[Dict]:
        """
        获取用户在指定租户的信息，并关联查询租户名称
        
        Args:
            user_id: 用户ID
            tenant_id: 租户ID
            
        Returns:
            包含租户用户信息和租户名称的字典
        """
        try:
            # 使用 join 关联查询 tenant 表
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
                # 转换为字典并添加 tenant_name
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

    def create_tenant(self, tenant_data: TenantCreateSchema, creator_id: str) -> TenantSchema:
        db_tenant = TenantModel(
            id=str(uuid.uuid4()).replace("-", ""),
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
        # 检查是否已存在相同的租户-用户关联
        existing = self.db.query(TenantUserModel).filter(
            TenantUserModel.tenant_id == tenant_user.tenant_id,
            TenantUserModel.user_id == tenant_user.user_id
        ).first()

        if existing:
            return None  # 已存在，不需要重复添加
        else:
            db_tenant_user = TenantUserModel(**tenant_user.model_dump(exclude={'tenant_name'}))
            self.db.add(db_tenant_user)
            self.db.commit()
            # 刷新对象以获取数据库生成的字段（如果有的话）
            self.db.refresh(db_tenant_user)
            # 将数据库模型转换为 Schema 对象
            return TenantUserSchema.model_validate(db_tenant_user)
    
    def get_user_by_id(self, user_id: str) -> Optional[UserMode]:
        return self.db.query(UserMode).filter((UserMode.id == user_id) & (UserMode.disabled == 0)).first()

    def get_tenant_users(self, tenant_id: str) -> List[TenantUserRoleSchema]:
        users = self.db.execute(
            select(TenantUserRoleModel).where(TenantUserRoleModel.tenant_id == tenant_id)
        )
        return [TenantUserRoleSchema.model_validate(u) for u in users.scalars()]

    def get_user_tenants(self, user_id: str) -> List[TenantUserSchema]:
        """获取用户的所有租户角色信息 - 同步方法"""
        users = self.db.execute(
            select(TenantUserModel).where(
                (TenantUserModel.user_id == user_id) &
                (TenantUserModel.role_type > 0)  # 获取所有有管理权限的角色
            )
        )
        return [TenantUserSchema.model_validate(u) for u in users.scalars()]

    def get_user(self, user_id: str) -> Optional[UserMode]:
        """根据用户ID获取用户信息 - 同步方法"""
        try:
            user = self.db.query(UserMode).filter(UserMode.id == user_id).first()
            return user
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return None

    def add_admin(self, tenant_id: str, user_id: str) -> bool:
        """设置用户为管理员 - 同步方法"""
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

    def delete_admin(self, tenant_id: str, user_id: str) -> bool:
        """取消用户的管理员权限（设置为普通用户）- 同步方法"""
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

    def get_tenant_user_role(self, tenant_id: str, user_id: str) -> Optional[TenantUserSchema]:
        """获取用户在租户中的角色信息 - 同步方法"""
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
        """
        删除租户用户
        只有租户管理员才能删除用户

        Args:
            tenant_id: 租户ID
            user_id_to_delete: 要删除的用户ID
            current_user_id: 当前操作的用户ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 首先验证当前用户是否是租户管理员且未被禁用
            from user.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.db)

            # 检查当前用户是否存在且未被禁用
            current_user = user_repo.get_user_by_id(current_user_id)
            if not current_user or current_user.disabled == 1:
                return False

            # 检查当前用户是否是租户管理员
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == current_user_id,
                TenantUserModel.role_type > 1  # 管理员角色
            ).first()

            if not tenant_user:
                return False

            # 删除指定的租户用户
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