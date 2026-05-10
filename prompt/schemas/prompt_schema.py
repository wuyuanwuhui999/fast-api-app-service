from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PromptSchema(BaseModel):
    """提示词 Schema"""
    id: str
    prompt: str
    tenant_id: str
    user_id: str
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class GetPromptParams(BaseModel):
    """查询提示词参数"""
    tenant_id: str


class UpdatePromptSchema(BaseModel):
    """更新提示词请求 Schema"""
    id: str = Field(..., description="提示词ID")
    prompt: str = Field(..., description="提示词内容", min_length=1, max_length=255)
    tenant_id: str = Field(..., description="租户ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc123def456",
                "prompt": "你是一个专业的AI助手，请用专业、友善的语气回答问题。",
                "tenant_id": "f96f89c075d611f0be3b002b67a509e7"
            }
        }
    )