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


class TenantSchema(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    status: int = 1
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    role_type: Optional[int] = None  # 用户在该租户的角色

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class TenantListResponse(BaseModel):
    data: List[TenantSchema]
    total: int

# 添加以下Schema
class TenantCreateSchema(BaseModel):
    name: str
    code: str
    description: Optional[str] = None

class TenantUpdateSchema(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None

class TenantUserRoleSchema(BaseModel):
    tenant_id: str
    user_id: str
    role_type: int = Field(..., ge=0, le=2)
    is_disabled: bool = False

class TenantUserRoleUpdateSchema(BaseModel):
    role_type: Optional[int] = Field(None, ge=0, le=2)
    is_disabled: Optional[bool] = None