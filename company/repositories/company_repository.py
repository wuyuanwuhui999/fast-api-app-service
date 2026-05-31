# company/repositories/company_repository.py
import uuid
from datetime import datetime
from typing import List, Optional, Any, Tuple, Dict

from sqlalchemy import select, delete, func, or_, and_, text
from sqlalchemy.orm import Session, joinedload

from common.models.common_model import UserMode
from company.models.company_model import CompanyModel, CompanyUserModel
from company.schemas.company_schema import (
    CompanySchema, CompanyUserSchema, CompanyUserDetailSchema
)
from fastapi.logger import logger


class CompanyRepository:
    """企业数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 企业相关 ====================
    
    def get_company_by_id(self, company_id: str) -> Optional[Any]:
        """根据公司ID查询公司是否存在"""
        try:
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            return company
        except Exception as e:
            logger.error(f"查询公司失败: {str(e)}")
            return None

    def get_companies_by_user_id(self, user_id: str) -> List[CompanySchema]:
        """
        根据用户ID查询用户所在的所有企业
        
        规则：
        1. code='personal' 的企业是所有用户共享的，直接查询出来，不需要根据用户关联过滤
        2. 其他企业需要通过 CompanyUserModel 关联查询用户加入的企业
        """
        try:
            company_dict = {}  # 使用字典去重，key为公司ID
            
            # 1. 查询所有用户共享的 personal 企业（无条件查询）
            personal_companies = self.db.query(CompanyModel).filter(
                CompanyModel.code == 'personal',
                CompanyModel.status == 1
            ).all()
            
            for company in personal_companies:
                company_dict[company.id] = company
            
            # 2. 查询用户关联的企业（排除 personal，因为 personal 已经添加过了）
            user_companies = (
                self.db.query(CompanyModel)
                .join(CompanyUserModel, CompanyModel.id == CompanyUserModel.company_id)
                .filter(
                    CompanyUserModel.user_id == user_id,
                    CompanyUserModel.status == 1,
                    CompanyModel.status == 1,
                    CompanyModel.code != 'personal'  # 排除 personal，避免重复
                )
                .order_by(CompanyUserModel.is_default.desc(), CompanyUserModel.join_date.desc())
                .all()
            )
            
            for company in user_companies:
                if company.id not in company_dict:
                    company_dict[company.id] = company
            
            # 3. 转换为列表
            result_list = list(company_dict.values())
            
            # 排序：personal 企业排在前面
            def sort_key(company):
                return 0 if company.code == 'personal' else 1
            
            result_list.sort(key=sort_key)
            
            return [CompanySchema.model_validate(c) for c in result_list]
            
        except Exception as e:
            logger.error(f"查询用户企业列表失败: {str(e)}", exc_info=True)
            return []

    # ==================== 企业用户相关 ====================
    
    def get_company_user(self, company_id: str, user_id: str) -> Optional[CompanyUserModel]:
        """查询用户在指定企业中的关联信息"""
        return self.db.query(CompanyUserModel).filter(
            CompanyUserModel.company_id == company_id,
            CompanyUserModel.user_id == user_id,
            CompanyUserModel.status == 1
        ).first()

    def get_user_role_in_company(self, company_id: str, user_id: str) -> int:
        """获取用户在指定企业中的角色（返回数字）"""
        # personal 企业特殊处理：所有用户都有访问权限
        company = self.db.query(CompanyModel).filter(
            CompanyModel.id == company_id,
            CompanyModel.status == 1
        ).first()
        
        if company and company.code == 'personal':
            # personal 企业返回普通成员角色（0）
            return 0
        
        # 非 personal 企业需要检查用户关联
        company_user = self.get_company_user(company_id, user_id)
        if not company_user:
            return -1  # 用户不在企业中
        return int(company_user.role) if company_user.role else 0

    def get_company_users_with_pagination(
        self,
        company_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[CompanyUserDetailSchema], int]:
        """分页查询企业用户列表"""
        try:
            offset = (page - 1) * page_size
            
            # 检查是否是 personal 企业
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            
            is_personal = company and company.code == 'personal'
            
            if is_personal:
                # personal 企业：查询所有用户（全平台共享）
                # 查询总数
                total = self.db.query(func.count(UserMode.id)).filter(
                    UserMode.disabled == 0
                ).scalar()
                
                # 查询分页数据
                results = (
                    self.db.query(UserMode)
                    .filter(UserMode.disabled == 0)
                    .order_by(UserMode.create_date.desc())
                    .offset(offset)
                    .limit(page_size)
                    .all()
                )
                
                users = []
                for user in results:
                    users.append(CompanyUserDetailSchema(
                        id="",  # personal 企业没有关联ID
                        user_id=user.id,
                        company_id=company_id,
                        role="0",  # personal 企业所有用户都是普通成员
                        status=1,
                        join_date=user.create_date,
                        username=user.username,
                        email=user.email,
                        avater=user.avater
                    ))
                
                return users, total if total else 0
            
            # 非 personal 企业：原有逻辑
            # 查询总数
            total = self.db.query(func.count(CompanyUserModel.id)).filter(
                CompanyUserModel.company_id == company_id,
                CompanyUserModel.status == 1
            ).scalar()

            # 查询分页数据
            results = (
                self.db.query(CompanyUserModel, UserMode)
                .join(UserMode, CompanyUserModel.user_id == UserMode.id)
                .filter(
                    CompanyUserModel.company_id == company_id,
                    CompanyUserModel.status == 1,
                    UserMode.disabled == 0
                )
                .order_by(
                    func.cast(CompanyUserModel.role, func.unsigned()).desc(),
                    CompanyUserModel.join_date.desc()
                )
                .offset(offset)
                .limit(page_size)
                .all()
            )

            users = []
            for company_user, user in results:
                users.append(CompanyUserDetailSchema(
                    id=company_user.id,
                    user_id=company_user.user_id,
                    company_id=company_user.company_id,
                    role=company_user.role,
                    status=company_user.status,
                    join_date=company_user.join_date,
                    username=user.username,
                    email=user.email,
                    avater=user.avater
                ))

            return users, total if total else 0

        except Exception as e:
            logger.error(f"查询企业用户列表失败: {str(e)}", exc_info=True)
            return [], 0

    def add_company_user(
        self,
        company_id: str,
        user_id: str,
        role: str,
        current_user_id: str
    ) -> Optional[CompanyUserSchema]:
        """添加用户到企业"""
        try:
            # 检查是否是 personal 企业
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            
            if company and company.code == 'personal':
                # personal 企业不需要添加用户关联，所有用户自动有权限
                # 直接返回成功
                return CompanyUserSchema(
                    id="",
                    user_id=user_id,
                    company_id=company_id,
                    role="0",
                    join_date=datetime.now(),
                    status=1,
                    create_by=current_user_id
                )
            
            # 检查是否已存在
            existing = self.db.query(CompanyUserModel).filter(
                CompanyUserModel.company_id == company_id,
                CompanyUserModel.user_id == user_id
            ).first()

            if existing:
                if existing.status == 0:
                    # 如果已存在但被禁用，重新启用
                    existing.status = 1
                    existing.role = role
                    existing.update_by = current_user_id
                    existing.update_date = datetime.now()
                    self.db.commit()
                    self.db.refresh(existing)
                    return CompanyUserSchema.model_validate(existing)
                return None  # 已存在且正常

            # 创建新关联
            db_company_user = CompanyUserModel(
                id=str(uuid.uuid4()).replace("-", ""),
                company_id=company_id,
                user_id=user_id,
                role=role,
                join_date=datetime.now(),
                status=1,
                create_by=current_user_id,
                create_date=datetime.now()
            )
            self.db.add(db_company_user)
            self.db.commit()
            self.db.refresh(db_company_user)
            return CompanyUserSchema.model_validate(db_company_user)

        except Exception as e:
            self.db.rollback()
            logger.error(f"添加企业用户失败: {str(e)}", exc_info=True)
            return None

    def update_user_role(
        self,
        company_id: str,
        user_id: str,
        new_role: str,
        current_user_id: str
    ) -> bool:
        """更新用户在企业中的角色"""
        try:
            # personal 企业不允许修改角色（所有用户都是普通成员）
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            
            if company and company.code == 'personal':
                logger.warning(f"personal 企业不允许修改用户角色")
                return False
            
            company_user = self.db.query(CompanyUserModel).filter(
                CompanyUserModel.company_id == company_id,
                CompanyUserModel.user_id == user_id,
                CompanyUserModel.status == 1
            ).first()

            if not company_user:
                return False

            company_user.role = new_role
            company_user.update_by = current_user_id
            company_user.update_date = datetime.now()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新用户角色失败: {str(e)}", exc_info=True)
            return False

    def remove_company_user(
        self,
        company_id: str,
        user_id: str,
        current_user_id: str
    ) -> bool:
        """从企业移除用户（软删除）"""
        try:
            # personal 企业不允许移除用户（所有用户自动拥有权限）
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            
            if company and company.code == 'personal':
                logger.warning(f"personal 企业不允许移除用户")
                return False
            
            company_user = self.db.query(CompanyUserModel).filter(
                CompanyUserModel.company_id == company_id,
                CompanyUserModel.user_id == user_id
            ).first()

            if not company_user:
                return False

            company_user.status = 0
            company_user.update_by = current_user_id
            company_user.update_date = datetime.now()
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"移除企业用户失败: {str(e)}", exc_info=True)
            return False

    def get_user_by_id(self, user_id: str) -> Optional[UserMode]:
        """根据用户ID获取用户信息"""
        return self.db.query(UserMode).filter(
            UserMode.id == user_id,
            UserMode.disabled == 0
        ).first()

    def check_company_exists(self, company_id: str) -> bool:
        """检查企业是否存在且启用"""
        company = self.db.query(CompanyModel).filter(
            CompanyModel.id == company_id,
            CompanyModel.status == 1
        ).first()
        return company is not None