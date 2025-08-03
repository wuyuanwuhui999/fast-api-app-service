from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    user_account: str
    email: EmailStr
    username: str

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

class UserInDB(UserBase):
    id: str
    user_account: str
    create_date: datetime
    update_date: datetime
    username: str
    telephone: Optional[str] = None
    email: Optional[EmailStr] = None
    avater: Optional[str] = None
    birthday: Optional[str] = None
    sex: Optional[str] = None
    role: Optional[str] = None
    sign: Optional[str] = None
    region: Optional[str] = None
    disabled: bool = False
    permission: int = 0

    class Config:
        from_attributes = True

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