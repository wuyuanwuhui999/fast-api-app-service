import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from company.repositories.company_repository import CompanyRepository
from company.schemas.company_schema import (
    CompanySchema, AddCompanyUserSchema, UpdateUserRoleSchema,
    RemoveUserSchema, CompanyUserDetailSchema
)


class CompanyService:
    """企业服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.company_repository = CompanyRepository(db)

    # ==================== 企业查询 ====================
    
    async def get_user_companies(self, current_user_id: str) -> ResultEntity:
        """获取当前用户所在的企业列表"""
        try:
            companies = self.company_repository.get_companies_by_user_id(current_user_id)
            return ResultUtil.success(data=companies, total=len(companies))
        except Exception as e:
            logger.error(f"获取用户企业列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取企业列表失败", data=None)

    async def get_users(
        self,
        company_id: str,
        page_num: int,
        page_size: int,
        current_user_id: str,
        keyword: Optional[str] = None  # 新增 keyword 参数
    ) -> ResultEntity:
        """
        获取系统用户列表
                
        返回数据包含：
        - 用户基本信息（user_account, username, telephone, email, sex, region, avater, sign）
        """
        try:
            users, total = self.company_repository.get_users_with_pagination(
                company_id, current_user_id, page_num, page_size, keyword
            )

            return ResultUtil.success(data=users, total=total)

        except Exception as e:
            logger.error(f"获取系统用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取用户列表失败", data=None)

    async def get_company_users(
        self,
        company_id: str,
        page_num: int,
        page_size: int,
        current_user_id: str,
        keyword: Optional[str] = None  # 新增 keyword 参数
    ) -> ResultEntity:
        """
        获取企业用户列表
        
        权限要求：当前用户在企业中的 role > 0 才能查询（SQL中EXISTS子查询自动处理）
        
        返回数据包含：
        - 用户基本信息（user_account, username, telephone, email, sex, region, avater, sign）
        - 职位信息（position_id, position_name）
        - 部门信息（department_id, department_name）
        """
        try:
            # 检查企业是否存在
            if not self.company_repository.check_company_exists(company_id):
                return ResultUtil.fail(msg="企业不存在", data=None)

            # 查询用户列表（内置权限检查：只有 role > 0 才能查询）
            users, total = self.company_repository.get_company_users_with_pagination(
                company_id, current_user_id, page_num, page_size, keyword
            )
            
            # 如果 total == 0，有两种情况：
            # 1. 用户无权限（角色<=0）
            # 2. 确实没有用户数据
            # 为了区分，我们单独检查权限
            if total == 0:
                user_role = self.company_repository.get_user_role_in_company(company_id, current_user_id)
                if user_role <= 0:
                    return ResultUtil.fail(msg="无权查看该企业用户列表", data=None)

            return ResultUtil.success(data=users, total=total)

        except Exception as e:
            logger.error(f"获取企业用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取用户列表失败", data=None)

    async def add_company_user(
        self,
        request: AddCompanyUserSchema,
        current_user_id: str
    ) -> ResultEntity:
        """
        添加用户到企业
        需要当前用户在企业中的角色 >= 1
        """
        try:
            # 检查企业是否存在
            if not self.company_repository.check_company_exists(request.company_id):
                return ResultUtil.fail(msg="企业不存在", data=None)

            # 权限检查
            current_user_role = self.company_repository.get_user_role_in_company(
                request.company_id, current_user_id
            )
            if current_user_role < 1:
                return ResultUtil.fail(msg="无权添加企业用户", data=None)

            # 检查目标用户是否存在
            target_user = self.company_repository.get_user_by_id(request.user_id)
            if not target_user:
                return ResultUtil.fail(msg="目标用户不存在", data=None)

            # 检查要添加的角色是否符合权限
            if not self._can_manage_role(current_user_role, int(request.role)):
                role_names = {0: "普通成员", 1: "管理员", 2: "人事", 3: "企业老板"}
                return ResultUtil.fail(
                    msg=f"无权设置角色为{role_names.get(int(request.role), '未知')}的用户",
                    data=None
                )

            # 添加用户到企业
            result = self.company_repository.add_company_user(
                request.company_id,
                request.user_id,
                request.role,
                current_user_id
            )

            if result is None:
                return ResultUtil.fail(msg="用户已存在于该企业中", data=None)

            return ResultUtil.success(data=result, msg="添加用户成功")

        except Exception as e:
            logger.error(f"添加企业用户失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"添加用户失败: {str(e)}", data=None)

    async def update_user_role(
        self,
        request: UpdateUserRoleSchema,
        current_user_id: str
    ) -> ResultEntity:
        """
        更新用户在企业中的角色
        权限规则：
        - role=3（老板）：可修改任何角色
        - role=2（人事）：可修改 role 0 和 1，不可修改 role 2 和 3
        - role=1（管理员）：可修改 role 0，不可修改 role 1,2,3
        """
        try:
            # 检查企业是否存在
            if not self.company_repository.check_company_exists(request.company_id):
                return ResultUtil.fail(msg="企业不存在", data=None)

            # 获取当前用户角色
            current_user_role = self.company_repository.get_user_role_in_company(
                request.company_id, current_user_id
            )
            if current_user_role < 1:
                return ResultUtil.fail(msg="无权修改用户角色", data=None)

            # 获取目标用户当前角色
            target_user_role = self.company_repository.get_user_role_in_company(
                request.company_id, request.user_id
            )
            if target_user_role < 0:
                return ResultUtil.fail(msg="目标用户不在该企业中", data=None)

            # 目标用户不存在
            target_user = self.company_repository.get_user_by_id(request.user_id)
            if not target_user:
                return ResultUtil.fail(msg="目标用户不存在", data=None)

            # 权限校验
            if not self._can_modify_role(current_user_role, target_user_role, int(request.role)):
                role_names = {0: "普通成员", 1: "管理员", 2: "人事", 3: "企业老板"}
                return ResultUtil.fail(
                    msg=f"无权将{role_names.get(target_user_role, '未知')}修改为{role_names.get(int(request.role), '未知')}",
                    data=None
                )

            # 更新角色
            success = self.company_repository.update_user_role(
                request.company_id,
                request.user_id,
                request.role,
                current_user_id
            )

            if not success:
                return ResultUtil.fail(msg="更新角色失败", data=None)

            # 获取更新后的用户信息
            updated_user = self.company_repository.get_company_user(request.company_id, request.user_id)
            if updated_user:
                result_data = {
                    "user_id": updated_user.user_id,
                    "company_id": updated_user.company_id,
                    "role": updated_user.role,
                    "username": target_user.username,
                    "email": target_user.email
                }
                return ResultUtil.success(data=result_data, msg="更新角色成功")
            else:
                return ResultUtil.success(msg="更新角色成功")

        except Exception as e:
            logger.error(f"更新用户角色失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"更新角色失败: {str(e)}", data=None)

    async def remove_company_user(
        self,
        request: RemoveUserSchema,
        current_user_id: str
    ) -> ResultEntity:
        """
        从企业移除用户
        需要当前用户角色 >= 1，且不能移除比自己角色高的用户
        """
        try:
            # 检查企业是否存在
            if not self.company_repository.check_company_exists(request.company_id):
                return ResultUtil.fail(msg="企业不存在", data=None)

            # 获取当前用户角色
            current_user_role = self.company_repository.get_user_role_in_company(
                request.company_id, current_user_id
            )
            if current_user_role < 1:
                return ResultUtil.fail(msg="无权移除企业用户", data=None)

            # 不能移除自己
            if request.user_id == current_user_id:
                return ResultUtil.fail(msg="不能移除自己", data=None)

            # 获取目标用户角色
            target_user_role = self.company_repository.get_user_role_in_company(
                request.company_id, request.user_id
            )
            if target_user_role < 0:
                return ResultUtil.fail(msg="目标用户不在该企业中", data=None)

            # 权限校验：不能移除比自己角色高的用户
            if target_user_role >= current_user_role and current_user_role < 3:
                role_names = {0: "普通成员", 1: "管理员", 2: "人事", 3: "企业老板"}
                return ResultUtil.fail(
                    msg=f"无权移除角色为{role_names.get(target_user_role, '未知')}的用户",
                    data=None
                )

            # 移除用户
            success = self.company_repository.remove_company_user(
                request.company_id,
                request.user_id,
                current_user_id
            )

            if not success:
                return ResultUtil.fail(msg="移除用户失败", data=None)

            return ResultUtil.success(msg="移除用户成功")

        except Exception as e:
            logger.error(f"移除企业用户失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"移除用户失败: {str(e)}", data=None)

    # ==================== 权限辅助方法 ====================
    
    def _can_manage_role(self, current_role: int, target_role: int) -> bool:
        """
        检查当前用户是否有权限设置目标角色
        
        Args:
            current_role: 当前用户角色
            target_role: 要设置的目标角色
        
        Returns:
            是否有权限
        """
        if current_role == 3:  # 老板可设置任何角色
            return True
        elif current_role == 2:  # 人事可设置0和1
            return target_role in [0, 1]
        elif current_role == 1:  # 管理员只能设置0
            return target_role == 0
        else:
            return False

    def _can_modify_role(self, current_role: int, target_current_role: int, new_role: int) -> bool:
        """
        检查当前用户是否有权限修改目标用户的角色
        
        Args:
            current_role: 当前用户角色
            target_current_role: 目标用户当前角色
            new_role: 要修改的新角色
        
        Returns:
            是否有权限
        """
        # 不能修改比自己角色高的用户
        if target_current_role >= current_role and current_role < 3:
            return False
        
        # 根据当前用户角色判断可以设置的新角色
        return self._can_manage_role(current_role, new_role)