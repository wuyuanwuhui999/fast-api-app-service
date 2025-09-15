from fastapi import APIRouter, Depends

from common.schemas.user_schema import UserSchema
from common.utils.result_util import ResultEntity
from tenant.schemas.tenants_schema import TenantUserRoleUpdateSchema, TenantUpdateSchema, TenantCreateSchema, \
    TenantAdminUpdateSchema
from tenant.services.tenants_service import TenantsService
from common.dependencies.auth_dependency import get_current_user

router = APIRouter(prefix="/service/tenant", tags=["tenant"])

@router.get("/getUserTenantList",response_model=ResultEntity)
async def get_user_tenants(
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取当前用户所属的所有租户"""
    return await tenants_service.get_user_tenant_list(current_user.id)


@router.get("/getTenantUser",response_model=ResultEntity)
async def get_user_tenant(
        tenantId:str,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取当前用户所属的所有租户"""
    return await tenants_service.get_tenant_user(current_user.id,tenantId)

# 在 router 中添加以下路由
@router.get("/getTenantUserList", response_model=ResultEntity)
async def get_tenant_users_with_pagination(
    tenantId: str,
    pageNum: int = 1,
    pageSize: int = 10,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取租户用户列表（分页）"""
    return await tenants_service.get_tenant_users_with_pagination(
        tenantId, pageNum, pageSize, current_user
    )

@router.post("/create_tenant",response_model=ResultEntity)
async def create_tenant(
    tenant_data: TenantCreateSchema,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """创建新租户（需要管理员权限）"""
    return await tenants_service.create_tenant(tenant_data, current_user)

@router.put("/update_tenant/{tenant_id}",response_model=ResultEntity)
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdateSchema,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """更新租户信息（需要租户管理员权限）"""
    return await tenants_service.update_tenant(tenant_id, update_data, current_user)

@router.delete("/delete_tenant/{tenant_id}",response_model=ResultEntity)
async def delete_tenant(
    tenant_id: str,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """删除租户（需要超级管理员权限）"""
    return await tenants_service.delete_tenant(tenant_id, current_user)

@router.post("/addTenantUser/{tenant_id}/{user_id}",response_model=ResultEntity)
async def add_tenant_user(
    tenant_id: str,
    user_id: str,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """管理租户用户（禁用/设置角色）"""
    return await tenants_service.add_tenant_user(tenant_id, user_id, current_user)

@router.get("/get_tenant_users/{tenant_id}",response_model=ResultEntity)
async def get_tenant_users(
    tenant_id: str,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """获取租户下的所有用户（需要租户管理员权限）"""
    return await tenants_service.get_tenant_users(tenant_id, current_user)

# 在 router 中添加以下路由

@router.post("/addAdmin", response_model=ResultEntity)
async def add_admin(
    tenant_data: TenantAdminUpdateSchema,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """设置用户为管理员（需要超级管理员权限）"""
    return await tenants_service.add_admin(tenant_data.tenantId, current_user.id, tenant_data.userId)

@router.delete("/deleteAdmin", response_model=ResultEntity)
async def delete_admin(
    tenant_data: TenantAdminUpdateSchema,
    current_user: UserSchema = Depends(get_current_user),
    tenants_service: TenantsService = Depends()
):
    """取消用户的管理员权限（需要超级管理员权限）"""
    return await tenants_service.delete_admin(tenant_data.tenantId, current_user.id, tenant_data.userId)

