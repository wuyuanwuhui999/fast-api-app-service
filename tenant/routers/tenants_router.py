from fastapi import APIRouter, Depends, Header, HTTPException, Query
from typing import Optional
from common.utils.result_util import ResultEntity
from tenant.schemas.tenants_schema import TenantUserRoleUpdateSchema, TenantUpdateSchema, TenantCreateSchema 
from tenant.services.tenants_service import TenantsService

router = APIRouter(prefix="/service/tenant", tags=["tenant"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getTenantList", response_model=ResultEntity)
async def get_tenant_list(
    companyId: str = Query(..., description="企业ID（必填）"),
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """获取当前用户所属的所有租户，支持按企业ID筛选"""
    return await tenants_service.get_tenant_list(current_user_id, companyId)


@router.get("/getTenantUser", response_model=ResultEntity)
async def get_user_tenant(
    tenantId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """获取当前用户所属的所有租户"""
    return await tenants_service.get_tenant_user(current_user_id, tenantId)


@router.get("/getTenantUserList", response_model=ResultEntity)
async def get_tenant_users_with_pagination(
    tenantId: str,
    pageNum: int = 1,
    pageSize: int = 10,
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/账号/电话/邮箱）"),
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """获取租户用户列表（分页），支持模糊搜索"""
    return await tenants_service.get_tenant_users_with_pagination(
        tenantId, pageNum, pageSize, keyword, current_user_id
    )


@router.post("/create_tenant", response_model=ResultEntity)
async def create_tenant(
    tenant_data: TenantCreateSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """创建新租户（需要管理员权限，必须携带company_id）"""
    return await tenants_service.create_tenant(tenant_data, current_user_id)


@router.put("/update_tenant/{tenant_id}", response_model=ResultEntity)
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdateSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """更新租户信息（需要租户管理员权限）"""
    return await tenants_service.update_tenant(tenant_id, update_data, current_user_id)


@router.delete("/delete_tenant/{tenant_id}", response_model=ResultEntity)
async def delete_tenant(
    tenant_id: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """删除租户（需要超级管理员权限）"""
    return await tenants_service.delete_tenant(tenant_id, current_user_id)


@router.post("/addTenantUser/{tenant_id}/{user_id}", response_model=ResultEntity)
async def add_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """管理租户用户（禁用/设置角色）"""
    return await tenants_service.add_tenant_user(tenant_id, user_id, current_user_id)


@router.get("/get_tenant_users/{tenant_id}", response_model=ResultEntity)
async def get_tenant_users(
    tenant_id: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """获取租户下的所有用户（需要租户管理员权限）"""
    return await tenants_service.get_tenant_users(tenant_id, current_user_id)


@router.post("/addAdmin/{tenantId}/{userId}", response_model=ResultEntity)
async def add_admin(
    tenantId: str,
    userId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """设置用户为管理员（需要超级管理员权限）"""
    return await tenants_service.add_admin(tenantId, current_user_id, userId)


@router.put("/cancelAdmin/{tenantId}/{userId}", response_model=ResultEntity)
async def cancel_admin(
    tenantId: str,
    userId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """取消用户的管理员权限（需要超级管理员权限）"""
    return await tenants_service.cancel_admin(tenantId, current_user_id, userId)


@router.delete("/deleteTenantUser/{tenantId}/{userId}", response_model=ResultEntity)
async def delete_tenant_user(
    tenantId: str,
    userId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """管理员删除租户"""
    return await tenants_service.delete_tenant_user(tenantId, userId, current_user_id)


@router.get("/searchUsers", response_model=ResultEntity)
async def search_users(
    companyId: str = Query(..., description="企业ID"),
    tenantId: str = Query(..., description="租户ID"),
    keyword: Optional[str] = Query(None, description="搜索关键词（用户名/账号/电话/邮箱）"),
    pageNum: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user_id: str = Depends(get_user_id_from_header),
    tenants_service: TenantsService = Depends()
):
    """
    搜索用户列表（支持模糊搜索）
    查询该企业下的所有用户，并标记是否已在该租户中
    """
    return await tenants_service.search_users(
        company_id=companyId,
        tenant_id=tenantId,
        keyword=keyword,
        page_num=pageNum,
        page_size=pageSize,
        current_user_id=current_user_id
    )