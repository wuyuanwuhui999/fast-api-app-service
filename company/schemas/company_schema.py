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
    status: int = 1
    role: int = 0
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
    position_id: Optional[str] = None
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
    """企业用户详情Schema（包含用户信息和职位信息）"""
    id: str
    user_id: str
    user_account: Optional[str] = None
    company_id: str
    role: str
    status: int
    join_date: Optional[datetime] = None
    # 用户基本信息
    username: Optional[str] = None
    email: Optional[str] = None
    avater: Optional[str] = None
    telephone: Optional[str] = None
    sex: Optional[str] = None
    region: Optional[str] = None
    sign: Optional[str] = None
    # 职位信息（通过 position_id 直接关联）
    position_id: Optional[str] = None
    position_name: Optional[str] = None
    # 部门信息（通过职位关联部门）
    department_id: Optional[str] = None
    department_name: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )

class AddCompanyUserSchema(BaseModel):
    """添加企业用户请求Schema"""
    companyId: str = Field(..., description="企业ID")
    userId: str = Field(..., description="用户ID")
    role: int = Field(default=0, alias="role", description="角色：0-普通成员，1-管理员，2-超级管理员")
    positionId: Optional[str] = Field(default=None, description="职位ID")


class UpdateUserRoleSchema(BaseModel):
    """更新用户角色请求Schema"""
    company_id: str = Field(..., description="企业ID")
    user_id: str = Field(..., description="用户ID")
    role: str = Field(..., description="新角色：0-普通成员，1-管理员，2-人事，3-企业老板")


class RemoveUserSchema(BaseModel):
    """移除用户请求Schema"""
    company_id: str = Field(..., description="企业ID")
    user_id: str = Field(..., description="用户ID")


# ==================== 部门相关 Schema ====================

class DepartmentSchema(BaseModel):
    """部门 Schema（响应模型）"""
    id: str = Field(..., description="部门ID")
    company_id: str = Field(..., description="所属企业ID", alias="companyId")
    department_name: str = Field(..., description="部门名称", alias="departmentName")
    description: Optional[str] = Field(None, description="部门描述")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


# ==================== 职位相关 Schema ====================

class PositionSchema(BaseModel):
    """职位 Schema（响应模型）"""
    id: str = Field(..., description="职位ID")
    position_name: str = Field(..., description="职位名称", alias="positionName")
    department_id: Optional[str] = Field(None, description="所属部门ID", alias="departmentId")
    description: Optional[str] = Field(None, description="职位描述")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )