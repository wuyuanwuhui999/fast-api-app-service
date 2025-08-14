from datetime import datetime
from typing import Optional
from pydantic import BaseModel


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