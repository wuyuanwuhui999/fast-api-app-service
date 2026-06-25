import uuid
from datetime import datetime

from sqlalchemy import select, delete, func, or_, and_, text
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
                TenantModel.code == user_id        # 公开租户
            )
            
            stmt = (
                select(TenantModel, TenantUserModel.role)
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
            for idx, (tenant, role) in enumerate(results):
                tenant_schema = TenantSchema.model_validate(tenant)
                tenant_schema.role = role if role is not None else 0
                result.append(tenant_schema)

            return result

        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            raise

    def get_tenant_user(self, user_id: str, tenant_id: str) -> Optional[Dict]:
        """获取用户在指定租户的信息，并关联查询用户表和租户名称"""
        try:
            from common.models.common_model import UserMode
            
            result = (
                self.db.query(
                    TenantUserModel,
                    TenantModel.name.label('tenant_name'),
                    UserMode.user_account.label('user_account'),
                    UserMode.username.label('username'),
                    UserMode.avater.label('avater'),
                    UserMode.disabled.label('user_disabled'),
                    UserMode.email.label('email')
                )
                .join(TenantModel, TenantModel.id == TenantUserModel.tenant_id)
                .join(UserMode, UserMode.id == TenantUserModel.user_id)
                .filter(
                    TenantUserModel.tenant_id == tenant_id,
                    TenantUserModel.user_id == user_id
                )
                .first()
            )
            
            if result:
                tenant_user, tenant_name, user_account, username, avater, user_disabled, email = result
                tenant_user_dict = {
                    'id': tenant_user.id,
                    'tenant_id': tenant_user.tenant_id,
                    'user_id': tenant_user.user_id,
                    'role': tenant_user.role,
                    'join_date': tenant_user.join_date,
                    'create_by': tenant_user.create_by,
                    'disabled': tenant_user.disabled,
                    'tenant_name': tenant_name,
                    # 关联查询的用户信息
                    'user_account': user_account,
                    'username': username,
                    'avater': avater,
                    'disabled': user_disabled,
                    'email': email
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
            page_size: int = 10,
            keyword: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        获取租户用户列表（分页）- 同步方法
        支持根据用户表中的 user_account、username、telephone、email 进行模糊搜索
        
        返回包含用户账号信息的字典列表
        """
        try:
            offset = (page - 1) * page_size
            
            # 处理搜索关键词
            search_value = keyword.strip() if keyword is not None and keyword.strip() else None

            # 查询总数
            total_stmt = (
                select(func.count())
                .select_from(TenantUserModel)
                .join(UserMode, TenantUserModel.user_id == UserMode.id)
                .where(TenantUserModel.tenant_id == tenant_id)
            )
            
            # 如果有关键词，添加模糊搜索条件
            if search_value:
                total_stmt = total_stmt.where(
                    or_(
                        UserMode.user_account.like(f"%{search_value}%"),
                        UserMode.username.like(f"%{search_value}%"),
                        UserMode.telephone.like(f"%{search_value}%"),
                        UserMode.email.like(f"%{search_value}%")
                    )
                )
            
            total = self.db.scalar(total_stmt)

            # 查询租户用户列表，并关联用户表获取用户信息
            stmt = (
                select(
                    TenantUserModel,
                    UserMode.user_account,
                    UserMode.username,
                    UserMode.email,
                    UserMode.avater,
                    UserMode.disabled.label('user_disabled'),
                    UserMode.telephone,
                    UserMode.sex,
                    UserMode.region
                )
                .join(UserMode, TenantUserModel.user_id == UserMode.id)
                .where(TenantUserModel.tenant_id == tenant_id)
                .order_by(TenantUserModel.join_date.desc())
                .offset(offset)
                .limit(page_size)
            )
            
            # 如果有关键词，添加模糊搜索条件
            if search_value:
                stmt = stmt.where(
                    or_(
                        UserMode.user_account.like(f"%{search_value}%"),
                        UserMode.username.like(f"%{search_value}%"),
                        UserMode.telephone.like(f"%{search_value}%"),
                        UserMode.email.like(f"%{search_value}%")
                    )
                )

            results = self.db.execute(stmt)
            
            # 构建包含用户信息的字典列表
            users = []
            for row in results:
                tenant_user, user_account, username, email, avater, user_disabled, telephone, sex, region = row
                users.append({
                    'id': tenant_user.id,
                    'tenant_id': tenant_user.tenant_id,
                    'user_id': tenant_user.user_id,
                    'role': tenant_user.role,
                    'join_date': tenant_user.join_date,
                    'create_by': tenant_user.create_by,
                    'disabled': tenant_user.disabled,
                    'user_account': user_account,
                    'username': username,
                    'email': email,
                    'avater': avater,
                    'user_disabled': user_disabled,
                    'telephone': telephone,
                    'sex': sex,
                    'region': region
                })

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
                (TenantUserModel.role > 0)
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
                tenant_user.role = 1
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"设置管理员失败: {str(e)}", exc_info=True)
            self.db.rollback()
            return False

    def cancel_admin(self, tenant_id: str, user_id: str) -> bool:
        try:
            tenant_user = self.db.query(TenantUserModel).filter(
                TenantUserModel.tenant_id == tenant_id,
                TenantUserModel.user_id == user_id
            ).first()

            if tenant_user and tenant_user.role >= 1:
                tenant_user.role = 0
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
                TenantUserModel.role > 1
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

    # ==================== 新增 search_users 方法 ====================
    
    def search_users(
            self,
            company_id: str,
            tenant_id: str,
            keyword: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> tuple[List[Dict[str, Any]], int]:
        """
        搜索用户列表（使用原生SQL）
        
        查询该企业下的所有用户，并标记是否已在该租户中
        
        Args:
            company_id: 企业ID
            tenant_id: 租户ID
            keyword: 搜索关键词（对 user_account, username, telephone, email 进行模糊搜索）
            page: 页码
            page_size: 每页数量
            
        Returns:
            (用户列表, 总数)
        """
        try:
            offset = (page - 1) * page_size
            
            # 处理搜索关键词
            search_value = keyword.strip() if keyword is not None and keyword.strip() else None

            # ==================== 查询记录集 ====================
            data_sql = """
                SELECT
                    u.id,
                    u.user_account,
                    u.username,
                    u.telephone,
                    u.email,
                    u.avater,
                    u.sex,
                    u.region,
                    u.create_date,
                    CASE
                        WHEN tu.id IS NOT NULL THEN 1
                        ELSE 0
                    END AS checked
                FROM `user` u
                LEFT JOIN `tenant_user` tu
                    ON u.id = tu.user_id
                    AND tu.tenant_id = :tenant_id
                WHERE
                    EXISTS (
                        SELECT 1
                        FROM `company_user` cu
                        WHERE cu.user_id = u.id
                        AND cu.company_id = :company_id
                        AND cu.status = 1
                    )
                    AND u.disabled = 0
                    AND
                    CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN
                        (
                            u.user_account LIKE CONCAT('%', :keyword, '%')
                            OR u.username LIKE CONCAT('%', :keyword, '%')
                            OR u.telephone LIKE CONCAT('%', :keyword, '%')
                            OR u.email LIKE CONCAT('%', :keyword, '%')
                        )
                        ELSE 1 = 1
                    END
                ORDER BY u.create_date DESC
                LIMIT :limit OFFSET :offset
            """
            
            result = self.db.execute(
                text(data_sql),
                {
                    "company_id": company_id,
                    "tenant_id": tenant_id,
                    "keyword": search_value,
                    "limit": page_size,
                    "offset": offset
                }
            )
            
            rows = result.fetchall()
            users = []
            for row in rows:
                user_dict = {
                    "id": row[0],
                    "user_account": row[1],
                    "username": row[2],
                    "telephone": row[3],
                    "email": row[4],
                    "avater": row[5],
                    "sex": row[6],
                    "region": row[7],
                    "create_date": row[8].strftime("%Y-%m-%d %H:%M:%S") if row[8] else None,
                    "checked": row[9]  # 1: 已在租户中, 0: 不在租户中
                }
                users.append(user_dict)

            # ==================== 查询总数 ====================
            count_sql = """
                SELECT COUNT(*)
                FROM `user` u
                WHERE
                    EXISTS (
                        SELECT 1
                        FROM `company_user` cu
                        WHERE cu.user_id = u.id
                        AND cu.company_id = :company_id
                        AND cu.status = 1
                    )
                    AND u.disabled = 0
                    AND
                    CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN
                        (
                            u.user_account LIKE CONCAT('%', :keyword, '%')
                            OR u.username LIKE CONCAT('%', :keyword, '%')
                            OR u.telephone LIKE CONCAT('%', :keyword, '%')
                            OR u.email LIKE CONCAT('%', :keyword, '%')
                        )
                        ELSE 1 = 1
                    END
            """
            
            total_result = self.db.execute(
                text(count_sql),
                {
                    "company_id": company_id,
                    "keyword": search_value
                }
            )
            total = total_result.scalar() or 0

            return users, total

        except Exception as e:
            logger.error(f"搜索用户列表失败: {str(e)}", exc_info=True)
            return [], 0