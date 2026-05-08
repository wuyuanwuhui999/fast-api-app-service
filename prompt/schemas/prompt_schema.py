from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


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