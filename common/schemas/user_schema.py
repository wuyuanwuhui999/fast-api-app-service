from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    user_account: str
    email: EmailStr
    username: str


class UserSchema(UserBase):
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
    disabled: int = 0
    permission: int = 0

    class Config:
        from_attributes = True