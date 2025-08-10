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