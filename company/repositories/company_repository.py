import uuid
from datetime import datetime
from typing import List, Optional, Any, Tuple, Dict

from sqlalchemy import select, delete, func, or_, and_, text
from sqlalchemy.orm import Session, joinedload

from common.models.common_model import UserMode
from company.models.company_model import CompanyModel, CompanyUserModel
from company.models.company_position import CompanyPosition
from company.models.company_department import CompanyDepartment
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
        1. code == user_id 的企业是所有用户共享的，直接查询出来，不需要根据用户关联过滤
        2. 其他企业需要通过 CompanyUserModel 关联查询用户加入的企业
        3. 返回数据中包含用户在该企业中的角色
        """
        try:
            company_list = []
            
            # 1. 查询所有用户共享的企业（code == user_id）
            shared_companies = self.db.query(CompanyModel).filter(
                CompanyModel.code == user_id,
                CompanyModel.status == 1
            ).all()
            
            for company in shared_companies:
                company_schema = CompanySchema.model_validate(company)
                company_schema.role = 0
                company_list.append(company_schema)
            
            # 2. 查询用户关联的企业（排除已经通过共享条件添加的企业）
            results = (
                self.db.query(
                    CompanyModel,
                    CompanyUserModel.role.label('user_role')
                )
                .join(
                    CompanyUserModel,
                    CompanyModel.id == CompanyUserModel.company_id
                )
                .filter(
                    CompanyUserModel.user_id == user_id,
                    CompanyUserModel.status == 1,
                    CompanyModel.status == 1,
                    CompanyModel.code != user_id
                )
                .order_by(
                    CompanyUserModel.is_default.desc(),
                    CompanyUserModel.join_date.desc()
                )
                .all()
            )
            
            for company, user_role in results:
                company_schema = CompanySchema.model_validate(company)
                company_schema.role = int(user_role) if user_role is not None else 0
                company_list.append(company_schema)
            
            return company_list
            
        except Exception as e:
            logger.error(f"查询用户企业列表失败: {str(e)}", exc_info=True)
            return []
    
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
            return 0
        
        # 非 personal 企业需要检查用户关联
        company_user = self.get_company_user(company_id, user_id)
        if not company_user:
            return -1
        return int(company_user.role) if company_user.role else 0

    def get_company_users_with_pagination(
        self,
        company_id: str,
        current_user_id: str,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        分页查询企业用户列表 - 使用原生SQL
        
        【重要】权限检查：SQL中的EXISTS子查询确保只有角色>0的用户才能查询
        
        关联查询：
        1. company_user -> user (INNER JOIN)
        2. company_user -> company_position (LEFT JOIN)
        3. company_position -> company_department (LEFT JOIN)
        
        Args:
            company_id: 企业ID
            current_user_id: 当前操作用户ID（用于权限检查）
            page: 页码，从1开始
            page_size: 每页数量
            keyword: 搜索关键词（可选，对username/user_account/telephone/email/id进行模糊匹配）
        
        Returns:
            Tuple[List[Dict], int]: (用户列表, 总记录数)
        """
        try:
            offset = (page - 1) * page_size
            
            # 处理搜索关键词（如果为None或空字符串，则跳过搜索条件）
            keyword = keyword.strip() if keyword is not None else ""
            search_value = keyword if keyword != '' and keyword is not None else None
            
            # ==================== 查询总数 ====================
            count_sql = """
                SELECT COUNT(*)
                FROM company_user cu
                INNER JOIN user u ON cu.user_id = u.id
                WHERE cu.company_id = :company_id
                AND cu.status = 1
                AND u.disabled = 0
                AND EXISTS (
                    SELECT role 
                    FROM company_user 
                    WHERE user_id = :current_user_id 
                        AND company_id = :company_id 
                        AND role > 0
                )
                AND
                CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN 
                (
                    u.username LIKE CONCAT('%', :keyword, '%')
                    OR u.user_account LIKE CONCAT('%', :keyword, '%')
                    OR u.telephone LIKE CONCAT('%', :keyword, '%')
                    OR u.email LIKE CONCAT('%', :keyword, '%')
                    OR u.id LIKE CONCAT('%', :keyword, '%')
                )
                ELSE 1 = 1
                END
            """
            
            total_result = self.db.execute(
                text(count_sql),
                {
                    "company_id": company_id,
                    "current_user_id": current_user_id,
                    "keyword": search_value
                }
            )
            total = total_result.scalar() or 0
            
            # 如果没有记录，直接返回空列表
            if total == 0:
                return [], 0
            
            # ==================== 查询数据列表 ====================
            data_sql = """
                SELECT
                    cu.id,
                    u.user_account,
                    u.username,
                    u.email,
                    u.avater,
                    u.telephone,
                    u.sex,
                    cu.role,
                    cu.position_id,
                    cp.position_name,
                    cp.department_id,
                    cd.department_name,
                    u.sign,
                    u.region,
                    cu.join_date,
                    cu.status
                FROM company_user cu
                INNER JOIN user u ON cu.user_id = u.id
                LEFT JOIN company_position cp ON cu.position_id = cp.id
                LEFT JOIN company_department cd ON cp.department_id = cd.id
                WHERE cu.company_id = :company_id
                AND cu.status = 1
                AND u.disabled = 0
                AND EXISTS (
                    SELECT role 
                    FROM company_user 
                    WHERE user_id = :current_user_id 
                        AND company_id = :company_id 
                        AND role > 0
                )
                AND
                CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN 
                    (
                        u.username LIKE CONCAT('%', :keyword, '%')
                        OR u.user_account LIKE CONCAT('%', :keyword, '%')
                        OR u.telephone LIKE CONCAT('%', :keyword, '%')
                        OR u.email LIKE CONCAT('%', :keyword, '%')
                        OR u.id LIKE CONCAT('%', :keyword, '%')
                    )
                    ELSE 1 = 1
                END
                ORDER BY CAST(cu.role AS UNSIGNED) DESC, cu.join_date ASC
                LIMIT :limit OFFSET :offset
            """
            
            result = self.db.execute(
                text(data_sql),
                {
                    "company_id": company_id,
                    "current_user_id": current_user_id,
                    "keyword": search_value,
                    "limit": page_size,
                    "offset": offset
                }
            )
            
            # 转换为字典列表
            rows = result.fetchall()
            users = []
            for row in rows:
                user_dict = {
                    "id": row[0],
                    "user_account": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avater": row[4],
                    "telephone": row[5],
                    "sex": row[6],
                    "role": int(row[7]) if row[7] is not None else 0,
                    "position_id": row[8],
                    "position_name": row[9],
                    "department_id": row[10],
                    "department_name": row[11],
                    "sign": row[12],
                    "region": row[13],
                    "join_date": row[14],
                    "status": row[15]
                }
                # 处理日期格式
                if user_dict["join_date"] and hasattr(user_dict["join_date"], 'strftime'):
                    user_dict["join_date"] = user_dict["join_date"].strftime("%Y-%m-%d %H:%M:%S")
                users.append(user_dict)
            
            return users, total

        except Exception as e:
            logger.error(f"获取企业用户列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_users_with_pagination(
        self,
        company_id: str,
        current_user_id: str,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        分页查询用户列表 - 使用原生SQL
        
        关联查询：
        1. user -> company_user (LEFT JOIN)
        
        Args:
            company_id: 企业ID，判断该用户是否在该企业内
            current_user_id: 当前操作用户ID（用于权限检查）
            page: 页码，从1开始
            page_size: 每页数量
            keyword: 搜索关键词（可选，对username/user_account/telephone/email/id进行模糊匹配）
        
        Returns:
            Tuple[List[Dict], int]: (用户列表, 总记录数)
        """
        try:
            offset = (page - 1) * page_size
            
            # 处理搜索关键词（如果为None或空字符串，则跳过搜索条件）
            keyword = keyword.strip() if keyword is not None else ""
            search_value = keyword if keyword != '' and keyword is not None else None
            
            # ==================== 查询总数 ====================
            count_sql = """
                SELECT COUNT(*)
                FROM user u
                WHERE u.disabled = 0
                AND u.role != 'system'
                AND
                CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN 
                (
                    u.username LIKE CONCAT('%', :keyword, '%')
                    OR u.user_account LIKE CONCAT('%', :keyword, '%')
                    OR u.telephone LIKE CONCAT('%', :keyword, '%')
                    OR u.email LIKE CONCAT('%', :keyword, '%')
                    OR u.id LIKE CONCAT('%', :keyword, '%')
                )
                ELSE 1 = 1
                END
            """
            
            total_result = self.db.execute(
                text(count_sql),
                {
                    "keyword": search_value
                }
            )
            total = total_result.scalar() or 0
            
            # 如果没有记录，直接返回空列表
            if total == 0:
                return [], 0
            
            # ==================== 查询数据列表 ====================
            data_sql = """
                SELECT
                    u.id,
                    u.user_account,
                    u.username,
                    u.email,
                    u.avater,
                    u.telephone,
                    u.birthday,
                    u.sex,
                    u.sign,
                    u.region,
                    u.create_date,
                    u.update_date,
                    CASE WHEN cu.user_id IS NOT NULL THEN 1 ELSE 0 END AS checked
                FROM user u
                LEFT JOIN company_user cu
                    ON cu.user_id = u.id
                    AND cu.company_id = :company_id
                    AND cu.status = 1
                WHERE u.disabled = 0
                AND u.role != 'system'
                AND
                CASE WHEN :keyword IS NOT NULL AND :keyword != '' THEN 
                    (
                        u.username LIKE CONCAT('%', :keyword, '%')
                        OR u.user_account LIKE CONCAT('%', :keyword, '%')
                        OR u.telephone LIKE CONCAT('%', :keyword, '%')
                        OR u.email LIKE CONCAT('%', :keyword, '%')
                        OR u.id LIKE CONCAT('%', :keyword, '%')
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
                    "keyword": search_value,
                    "limit": page_size,
                    "offset": offset
                }
            )
            
            # 转换为字典列表
            rows = result.fetchall()
            users = []
            for row in rows:
                user_dict = {
                    "id": row[0],
                    "user_account": row[1],
                    "username": row[2],
                    "email": row[3],
                    "avater": row[4],
                    "telephone": row[5],
                    "birthday": row[6],
                    "sex": row[7],
                    "sign": row[8],
                    "region": row[9],
                    "create_date": row[10],
                    "update_date": row[11],
                    "checked": row[12]  # 是否已在该企业内
                }
                # 处理日期格式
                if user_dict["create_date"] and hasattr(user_dict["create_date"], 'strftime'):
                    user_dict["create_date"] = user_dict["create_date"].strftime("%Y-%m-%d %H:%M:%S")
                if user_dict["update_date"] and hasattr(user_dict["update_date"], 'strftime'):
                    user_dict["update_date"] = user_dict["update_date"].strftime("%Y-%m-%d %H:%M:%S")
                users.append(user_dict)
            
            return users, total

        except Exception as e:
            logger.error(f"查询系统用户列表失败: {str(e)}", exc_info=True)
            return [], 0

    def add_company_user(
        self,
        company_id: str,
        user_id: str,
        role: str,
        current_user_id: str,
        position_id: Optional[str] = None
    ) -> Optional[CompanyUserSchema]:
        """添加用户到企业"""
        try:
            # 检查是否是 personal 企业
            company = self.db.query(CompanyModel).filter(
                CompanyModel.id == company_id,
                CompanyModel.status == 1
            ).first()
            
            if company and company.code == 'personal':
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
                    existing.status = 1
                    existing.role = role
                    if position_id is not None:
                        existing.position_id = position_id
                    self.db.commit()
                    self.db.refresh(existing)
                    return CompanyUserSchema.model_validate(existing)
                return None

            # 创建新关联
            db_company_user = CompanyUserModel(
                id=str(uuid.uuid4()).replace("-", ""),
                company_id=company_id,
                user_id=user_id,
                role=role,
                position_id=position_id,
                join_date=datetime.now(),
                status=1,
                create_by=current_user_id
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

    # ==================== 部门相关 ====================

    def get_departments_by_company_id(
        self, 
        company_id: str, 
        current_user_id: str
    ) -> List[Dict[str, Any]]:
        """
        根据公司ID查询所有部门（根据用户角色过滤）
        
        权限规则：用户在企业中的角色必须 <= 部门所需的角色
        
        Args:
            company_id: 企业ID
            current_user_id: 当前登录用户ID
            
        Returns:
            List[Dict]: 部门列表（不包含 role 字段）
        """
        try:
            from company.models.company_department import CompanyDepartment
            from company.models.company_model import CompanyUserModel
            
            # 使用 SQLAlchemy 查询，关联 company_user 表获取用户角色
            results = (
                self.db.query(
                    CompanyDepartment.id,
                    CompanyDepartment.company_id,
                    CompanyDepartment.department_name,
                    CompanyDepartment.description,
                    CompanyDepartment.create_time
                    # 注意：不查询 role 字段，不返回给前端
                )
                .join(
                    CompanyUserModel,
                    CompanyUserModel.company_id == CompanyDepartment.company_id
                )
                .filter(
                    CompanyDepartment.company_id == company_id,
                    CompanyUserModel.user_id == current_user_id,
                    CompanyUserModel.status == 1,
                    # 用户角色必须小于或等于部门所需的角色
                    CompanyUserModel.role <= CompanyDepartment.role
                )
                .order_by(
                    CompanyDepartment.role.asc(),  # 按角色升序（权限要求低的在前）
                    CompanyDepartment.create_time.desc()
                )
                .all()
            )
            
            return [
                {
                    "id": dept.id,
                    "company_id": dept.company_id,
                    "department_name": dept.department_name,
                    "description": dept.description,
                    "create_time": dept.create_time.strftime("%Y-%m-%d %H:%M:%S") if dept.create_time else None
                    # 不返回 role 字段
                }
                for dept in results
            ]
            
        except Exception as e:
            logger.error(f"查询部门列表失败: {str(e)}", exc_info=True)
            return []

    # ==================== 职位相关 ====================

    def get_positions_by_department_id(self, department_id: str) -> List[Dict[str, Any]]:
        """
        根据部门ID查询所有职位
        
        Args:
            department_id: 部门ID
            
        Returns:
            List[Dict]: 职位列表
        """
        try:
            from company.models.company_position import CompanyPosition
            
            positions = self.db.query(CompanyPosition).filter(
                CompanyPosition.department_id == department_id
            ).order_by(
                CompanyPosition.create_time.desc()
            ).all()
            
            return [
                {
                    "id": pos.id,
                    "position_name": pos.position_name,
                    "department_id": pos.department_id,
                    "description": pos.description,
                    "create_time": pos.create_time.strftime("%Y-%m-%d %H:%M:%S") if pos.create_time else None
                }
                for pos in positions
            ]
            
        except Exception as e:
            logger.error(f"查询职位列表失败: {str(e)}", exc_info=True)
            return []