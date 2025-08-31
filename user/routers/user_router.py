from fastapi import APIRouter, Depends, Query

from user.models.user_model import LoginForm
from common.schemas.user_schema import UserInDB
from user.schemas.user_schema import UserCreate, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest
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

@router.get("/user-getway/searchUsers", response_model=ResultEntity)
async def search_users(
    keyword: str = Query(..., description="搜索关键词"),
    tenantId:str = Query(0, description="租户id"),
    pageNum: int = Query(0, description="跳过记录数"),
    pageSize: int = Query(100, description="返回记录数"),
    current_user: UserInDB = Depends(get_current_user),
    user_service: UserService = Depends()
):
    """
    模糊查询用户列表
    根据用户名、账号、邮箱、电话进行模糊搜索
    """
    return await user_service.search_users(keyword,tenantId, (pageNum - 1) * pageSize, pageSize)
