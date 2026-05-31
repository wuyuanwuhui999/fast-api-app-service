# company/schemas/company_schema.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class CompanySchema(BaseModel):
    """企业Schema"""
    id: str
    name: str
    code: str
    description: Optional[str] = None
    # logo: Optional[str] = None  # 暂时注释
    status: int = 1
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class CompanyUserSchema(BaseModel):
    """企业用户关联Schema"""
    id: str
    user_id: str
    company_id: str
    is_default: int = 0
    role: str = "0"
    join_date: datetime
    status: int = 1
    create_by: str
    username: Optional[str] = None
    email: Optional[str] = None
    avater: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class CompanyUserDetailSchema(BaseModel):
    """企业用户详情Schema（包含用户信息）"""
    id: str
    user_id: str
    company_id: str
    role: str
    status: int
    join_date: Optional[datetime] = None
    username: Optional[str] = None
    email: Optional[str] = None
    avater: Optional[str] = None


class AddCompanyUserSchema(BaseModel):
    """添加企业用户请求Schema"""
    company_id: str = Field(..., description="企业ID")
    user_id: str = Field(..., description="用户ID")
    role: str = Field(default="0", description="角色：0-普通成员，1-管理员，2-人事，3-企业老板")


class UpdateUserRoleSchema(BaseModel):
    """更新用户角色请求Schema"""
    company_id: str = Field(..., description="企业ID")
    user_id: str = Field(..., description="用户ID")
    role: str = Field(..., description="新角色：0-普通成员，1-管理员，2-人事，3-企业老板")


class RemoveUserSchema(BaseModel):
    """移除用户请求Schema"""
    company_id: str = Field(..., description="企业ID")
    user_id: str = Field(..., description="用户ID")


class CompanyListResponse(BaseModel):
    """公司列表响应"""
    data: List[CompanySchema]
    total: int


class CompanyUserListResponse(BaseModel):
    """企业用户列表响应"""
    data: List[CompanyUserDetailSchema]
    total: int