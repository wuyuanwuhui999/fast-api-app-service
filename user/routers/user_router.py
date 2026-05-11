from fastapi import APIRouter, Depends, Query, Header, HTTPException

from user.models.user_model import LoginForm
from common.schemas.user_schema import UserSchema
from user.schemas.user_schema import UserCreate, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest
from user.services.auth_service import AuthService
from user.services.user_service import UserService
from user.dependencies.user_dependency import get_auth_service
from common.utils.result_util import ResultEntity

router = APIRouter(prefix="/service", tags=["user"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID（用于需要用户身份但已由网关验证的场景）"""
    return x_user_id


@router.post("/user/register", response_model=ResultEntity)
async def register(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.register_user(user)


@router.post("/user/login", response_model=ResultEntity)
async def login(form_data: LoginForm, auth_service: AuthService = Depends(get_auth_service)):
    return await auth_service.login(form_data.userAccount, form_data.password)


@router.get("/user/getUserData", response_model=ResultEntity)
async def get_user_data(
    current_user_id: str = Depends(get_user_id_from_header),
    user_service: UserService = Depends()
):
    # 通过user_id获取用户信息
    user = user_service.user_repository.get_user_by_id(current_user_id)
    from common.schemas.user_schema import UserSchema
    user_data = UserSchema.model_validate(user).dict()
    from common.utils.result_util import ResultUtil
    from common.utils.jwt_util import create_access_token
    token = create_access_token(data={"sub": user_data})
    return ResultUtil.success(data=user_data, token=token)


@router.put("/user/updateUser", response_model=ResultEntity)
async def update_user(
    user_update: UserUpdate,
    current_user_id: str = Depends(get_user_id_from_header),
    user_service: UserService = Depends()
):
    return await user_service.update_user(current_user_id, user_update)


@router.put("/user/updatePassword", response_model=ResultEntity)
async def update_password(
    password_change: PasswordChange,
    current_user_id: str = Depends(get_user_id_from_header),
    user_service: UserService = Depends()
):
    # 需要获取用户账号，这里简化处理
    user = user_service.user_repository.get_user_by_id(current_user_id)
    return await user_service.update_password(user.user_account, password_change)


@router.post("/user/sendEmailVertifyCode", response_model=ResultEntity)
async def send_email_verify_code(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.send_email_verify_code(mail_request)


@router.post("/user/resetPassword", response_model=ResultEntity)
async def reset_password(reset_request: ResetPasswordConfirm, user_service: UserService = Depends()):
    return await user_service.reset_password(reset_request)


@router.post("/user/loginByEmail", response_model=ResultEntity)
async def login_by_email(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.login_by_email(mail_request)


@router.post("/user/vertifyUser", response_model=ResultEntity)
async def verify_user(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.verify_user(user)


@router.get("/user/searchUsers", response_model=ResultEntity)
async def search_users(
    keyword: str = Query(..., description="搜索关键词"),
    tenantId: str = Query("", description="租户id"),
    pageNum: int = Query(1, description="页码"),
    pageSize: int = Query(100, description="返回记录数"),
    user_service: UserService = Depends()
):
    """模糊查询用户列表"""
    return await user_service.search_users(keyword, tenantId, (pageNum - 1) * pageSize, pageSize)