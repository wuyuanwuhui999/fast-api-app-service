from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class TenantSchema(BaseModel):
    id: str
    company_id: str  # 新增
    name: str
    code: str
    description: Optional[str] = None
    status: int = 1
    create_date: Optional[datetime] = None
    update_date: Optional[datetime] = None
    role: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class TenantUserSchema(BaseModel):
    id: str = Field(..., description="主键ID")
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    role: int = Field(..., description="角色类型：0-普通用户，1-租户管理员，2-超级管理员")
    join_date: datetime = Field(..., description="加入时间")
    create_by: str = Field(..., description="创建人ID")
    disabled: Optional[int] = None
    tenant_name: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class TenantCreateSchema(BaseModel):
    name: str
    code: str
    company_id: str  # 新增必填字段
    description: Optional[str] = None


class TenantUpdateSchema(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None


class TenantUserRoleSchema(BaseModel):
    tenant_id: str
    user_id: str
    role: int = Field(..., ge=0, le=2)
    disabled: bool = False


class TenantUserRoleUpdateSchema(BaseModel):
    role: Optional[int] = Field(None, ge=0, le=2)
    disabled: Optional[bool] = None


class TenantAdminUpdateSchema(BaseModel):
    directory: str
    tenantId: str


class TenantUsersQuerySchema(BaseModel):
    tenant_id: str
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=20, description="每页数量")


class TenantListResponse(BaseModel):
    data: List[TenantSchema]
    total: int