from fastapi import APIRouter, Depends

from common.schemas.user_schema import UserInDB
from tenant.schemas.tenants_schema import TenantUserRoleUpdateSchema, TenantUpdateSchema, TenantCreateSchema
from tenant.services.tenants_service import TenantsService
from common.dependencies.auth_dependency import get_current_user

router = APIRouter(prefix="/service/tenant", tags=["tenant"])

@router.get("/getUserTenants")
async def get_user_tenants(
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取当前用户所属的所有租户"""
    return await tenants_service.get_user_tenants(current_user.id)

@router.post("/tenants")
async def create_tenant(
    tenant_data: TenantCreateSchema,
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """创建新租户（需要管理员权限）"""
    return await tenants_service.create_tenant(tenant_data, current_user)

@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdateSchema,
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """更新租户信息（需要租户管理员权限）"""
    return await tenants_service.update_tenant(tenant_id, update_data, current_user)

@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """删除租户（需要超级管理员权限）"""
    return await tenants_service.delete_tenant(tenant_id, current_user)

@router.post("/tenants/{tenant_id}/users/{user_id}")
async def manage_tenant_user(
    tenant_id: str,
    user_id: str,
    role_data: TenantUserRoleUpdateSchema,
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """管理租户用户（禁用/设置角色）"""
    return await tenants_service.manage_tenant_user(tenant_id, user_id, role_data, current_user)

@router.get("/tenants/{tenant_id}/users")
async def get_tenant_users(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取租户下的所有用户（需要租户管理员权限）"""
    return await tenants_service.get_tenant_users(tenant_id, current_user)
