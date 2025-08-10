from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from typing import Optional, List

from common.schemas.user_schema import UserBase


class UserCreate(UserBase):
    password: str
    telephone: Optional[str] = None
    birthday: Optional[str] = None
    sex: Optional[int] = None
    sign: Optional[str] = None
    region: Optional[str] = None


class UserUpdate(BaseModel):
    username: Optional[str] = None
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    birthday: Optional[str] = None
    sex: Optional[int] = None
    sign: Optional[str] = None
    region: Optional[str] = None


class PasswordChange(BaseModel):
    oldPassword: str
    newPassword: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    email: EmailStr
    code: int
    new_password: str


class MailRequest(BaseModel):
    email: EmailStr
    subject: Optional[str] = None
    text: Optional[str] = None
    code: Optional[str] = None