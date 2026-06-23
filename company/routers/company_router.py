from fastapi import APIRouter, Depends, Header, HTTPException, Query
from typing import Optional
from common.utils.result_util import ResultEntity
from company.services.company_service import CompanyService
from company.schemas.company_schema import (
    AddCompanyUserSchema, UpdateUserRoleSchema, RemoveUserSchema
)

router = APIRouter(prefix="/service/company", tags=["company"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getCompanyList", response_model=ResultEntity)
async def get_company_list(
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """获取当前用户所在的公司列表"""
    return await company_service.get_user_companies(current_user_id)

@router.get("/getCompanyUsers", response_model=ResultEntity)
async def get_company_users(
    companyId: str = Query(..., description="企业ID"),
    pageNum: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/账号/电话/邮箱/ID）"),
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """获取企业用户列表（需要企业管理员权限）"""
    return await company_service.get_company_users(companyId, pageNum, pageSize, current_user_id, keyword)


@router.get("/searchUsers", response_model=ResultEntity)
async def get_users(
    companyId: str = Query(..., description="企业ID"),
    pageNum: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/账号/电话/邮箱/ID）"),
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """获取企业用户列表（需要企业管理员权限）"""
    return await company_service.get_users(companyId, pageNum, pageSize, current_user_id, keyword)


@router.post("/addUser", response_model=ResultEntity)
async def add_company_user(
    request: AddCompanyUserSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """添加用户到企业（需要企业管理员权限）"""
    return await company_service.add_company_user(request, current_user_id)


@router.put("/updateUserRole", response_model=ResultEntity)
async def update_user_role(
    request: UpdateUserRoleSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """
    修改用户在企业中的角色
    权限规则：
    - role=2（超级管理员）：可修改 role 0 和 1
    - role=1（管理员）：可修改 role 0
    """
    return await company_service.update_user_role(request, current_user_id)


@router.delete("/removeUser", response_model=ResultEntity)
async def remove_company_user(
    request: RemoveUserSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: CompanyService = Depends()
):
    """从企业移除用户（需要企业管理员权限）"""
    return await company_service.remove_company_user(request, current_user_id)