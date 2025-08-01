from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from user.schemas.user import UserCreate, UserInDB, UserUpdate, PasswordChange, ResetPasswordRequest, ResetPasswordConfirm, MailRequest
from user.services.auth import AuthService
from user.services.user import UserService
from user.dependencies.dependencies import get_auth_service  # Add this import
from user.dependencies.auth import get_current_user
from typing import List

router = APIRouter(prefix="/service", tags=["user"])

@router.post("/user/register", response_model=UserInDB)
async def register(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.register_user(user)

@router.post("/user/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends(get_auth_service)):  # Modified this line
    return await auth_service.login(form_data.username, form_data.password)

@router.get("/user-getway/getUserData", response_model=UserInDB)
async def get_user_data(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.put("/user-getway/update", response_model=UserInDB)
async def update_user(user_update: UserUpdate, current_user: UserInDB = Depends(get_current_user), user_service: UserService = Depends()):
    return await user_service.update_user(current_user.id, user_update)

@router.put("/user-getway/updatePassword")
async def update_password(password_change: PasswordChange, current_user: UserInDB = Depends(get_current_user), user_service: UserService = Depends()):
    return await user_service.update_password(current_user.id, password_change)

@router.post("/user/sendEmailVertifyCode")
async def send_email_verify_code(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.send_email_verify_code(mail_request)

@router.post("/user-getway/resetPassword")
async def reset_password(reset_request: ResetPasswordConfirm, user_service: UserService = Depends()):
    return await user_service.reset_password(reset_request)

@router.post("/user/loginByEmail")
async def login_by_email(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.login_by_email(mail_request)

@router.post("/user/vertifyUser")
async def verify_user(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.verify_user(user)