from fastapi import APIRouter, Depends

from user.models.user_model import LoginForm
from common.schemas.user_schema import UserInDB
from user.schemas.user_schema import UserCreate, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest, \
    TenantUserRoleUpdateSchema, TenantUpdateSchema, TenantCreateSchema
from user.services.auth_service import AuthService
from user.services.user_service import UserService
from user.dependencies.user_dependency import get_auth_service  # Add this import
from common.dependencies.auth_dependency import get_current_user
from common.utils.result_util import ResultEntity

router = APIRouter(prefix="/service", tags=["user"])


@router.post("/user/register", response_model=UserInDB)
async def register(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.register_user(user)


@router.post("/user/login", response_model=ResultEntity)
async def login(form_data: LoginForm, auth_service: AuthService = Depends(get_auth_service)):  # Modified this line
    return await auth_service.login(form_data.userAccount, form_data.password)


@router.get("/user-getway/getUserData", response_model=ResultEntity)
async def get_user_data(current_user: UserInDB = Depends(get_current_user), user_service: UserService = Depends()):
    return await user_service.get_user_data(current_user)


@router.put("/user-getway/updateUser", response_model=ResultEntity)
async def update_user(user_update: UserUpdate, current_user: UserInDB = Depends(get_current_user),
                      user_service: UserService = Depends()):
    return await user_service.update_user(current_user.id, user_update)


@router.put("/user-getway/updatePassword", response_model=ResultEntity)
async def update_password(password_change: PasswordChange, current_user: UserInDB = Depends(get_current_user),
                          user_service: UserService = Depends()):
    return await user_service.update_password(current_user.userAccount, password_change)


@router.post("/user/sendEmailVertifyCode", response_model=ResultEntity)
async def send_email_verify_code(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.send_email_verify_code(mail_request)


@router.post("/user-getway/resetPassword", response_model=ResultEntity)
async def reset_password(reset_request: ResetPasswordConfirm, user_service: UserService = Depends()):
    return await user_service.reset_password(reset_request)


@router.post("/user/loginByEmail", response_model=ResultEntity)
async def login_by_email(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.login_by_email(mail_request)


@router.post("/user/vertifyUser", response_model=ResultEntity)
async def verify_user(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.verify_user(user)

@router.get("/getUserTenants")
async def get_user_tenants(
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """获取当前用户所属的所有租户"""
    return await user_service.get_user_tenants(current_user.id)

@router.post("/tenants")
async def create_tenant(
    tenant_data: TenantCreateSchema,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """创建新租户（需要管理员权限）"""
    return await user_service.create_tenant(tenant_data, current_user)

@router.put("/tenants/{tenant_id}")
async def update_tenant(
    tenant_id: str,
    update_data: TenantUpdateSchema,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """更新租户信息（需要租户管理员权限）"""
    return await user_service.update_tenant(tenant_id, update_data, current_user)

@router.delete("/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """删除租户（需要超级管理员权限）"""
    return await user_service.delete_tenant(tenant_id, current_user)

@router.post("/tenants/{tenant_id}/users/{user_id}")
async def manage_tenant_user(
    tenant_id: str,
    user_id: str,
    role_data: TenantUserRoleUpdateSchema,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """管理租户用户（禁用/设置角色）"""
    return await user_service.manage_tenant_user(tenant_id, user_id, role_data, current_user)

@router.get("/tenants/{tenant_id}/users")
async def get_tenant_users(
    tenant_id: str,
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """获取租户下的所有用户（需要租户管理员权限）"""
    return await user_service.get_tenant_users(tenant_id, current_user)
