from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.schemas.user import UserCreate, UserInDB, UserUpdate, PasswordChange, ResetPasswordRequest, ResetPasswordConfirm, MailRequest
from app.services.user import UserService
from app.services.auth import AuthService
from app.dependencies.auth import get_current_user
from typing import List

router = APIRouter(prefix="/service/user", tags=["user"])

@router.post("/register", response_model=UserInDB)
async def register(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.register_user(user)

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), auth_service: AuthService = Depends()):
    return await auth_service.login(form_data.username, form_data.password)

@router.get("/me", response_model=UserInDB)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user

@router.put("/update", response_model=UserInDB)
async def update_user(user_update: UserUpdate, current_user: UserInDB = Depends(get_current_user), user_service: UserService = Depends()):
    return await user_service.update_user(current_user.id, user_update)

@router.put("/updatePassword")
async def update_password(password_change: PasswordChange, current_user: UserInDB = Depends(get_current_user), user_service: UserService = Depends()):
    return await user_service.update_password(current_user.id, password_change)

@router.post("/sendEmailVertifyCode")
async def send_email_verify_code(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.send_email_verify_code(mail_request)

@router.post("/resetPassword")
async def reset_password(reset_request: ResetPasswordConfirm, user_service: UserService = Depends()):
    return await user_service.reset_password(reset_request)

@router.post("/loginByEmail")
async def login_by_email(mail_request: MailRequest, user_service: UserService = Depends()):
    return await user_service.login_by_email(mail_request)

@router.post("/vertifyUser")
async def verify_user(user: UserCreate, user_service: UserService = Depends()):
    return await user_service.verify_user(user)