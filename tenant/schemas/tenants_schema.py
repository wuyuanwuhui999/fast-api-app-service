from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


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


class TenantUserSchema(BaseModel):
    """
    租户用户关联表 Schema
    """
    id: str = Field(..., description="主键ID")
    tenant_id: str = Field(..., description="租户ID")
    user_id: str = Field(..., description="用户ID")
    role_type: int = Field(..., description="角色类型：0-普通用户，1-租户管理员，2-超级管理员")
    join_date: datetime = Field(..., description="加入时间")
    create_by: str = Field(..., description="创建人ID")
    disabled: Optional[int] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


# 在 tenants_schema.py 末尾添加
class TenantUsersQuerySchema(BaseModel):
    tenant_id: str
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=20, description="每页数量")

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
    disabled: bool = False


class TenantUserRoleUpdateSchema(BaseModel):
    role_type: Optional[int] = Field(None, ge=0, le=2)
    disabled: Optional[bool] = None

# 在 tenants_schema.py 末尾添加
class TenantAdminUpdateSchema(BaseModel):
    userId: str
    tenantId: str