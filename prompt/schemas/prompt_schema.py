from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PromptSchema(BaseModel):
    title: str
    content: str
    disabled: int = 0
    industry: Optional[str] = None
    tags: Optional[str] = None


class PromptCreateSchema(PromptSchema):
    tenant_id: str
    user_id: str
    created_by: str


class PromptUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    disabled: Optional[int] = None
    industry: Optional[str] = None
    tags: Optional[str] = None
    updated_by: Optional[str] = None


class PromptInDBSchema(PromptSchema):
    id: str
    tenant_id: str
    user_id: str
    create_date: datetime
    update_date: Optional[datetime] = None
    created_by: str
    updated_by: Optional[str] = None

    class Config:
        orm_mode = True


class Prompt(PromptInDBSchema):
    pass

class PromptCategorySchema(BaseModel):
    id: str
    category: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

class PromptSystemShema(BaseModel):
    id:str
    categoryId: Optional[str] = Field(None, description="分类id")
    prompt: Optional[str] = Field(None, description="提示词内容")
    disabled: Optional[int] = Field(0, description="是否禁用：0-启用，1-禁用")
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

class PromptCollectShema(BaseModel):
    id:str
    prompt_id: Optional[str] = Field(None, description="提示词id")
    prompt: Optional[str] = Field(None, description="提示词")
    category_id: Optional[str] = Field(None, description="分类id")
    tenant_id: Optional[str] = Field(None, description="租户id")
    user_id: Optional[str] = Field(None, description="用户id")
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


