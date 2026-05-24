# agent/schemas/agent_schema.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ChatHistorySchema(BaseModel):
    """聊天历史记录 Schema"""
    id: Optional[int] = None
    user_id: Optional[str] = None
    files: Optional[str] = None
    chat_id: Optional[str] = None
    prompt: Optional[str] = None
    content: Optional[str] = None
    model_id: Optional[str] = None
    create_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class ChatHistoryResponseSchema(BaseModel):
    """聊天历史响应 Schema"""
    id: Optional[int] = None
    user_id: Optional[str] = None
    files: Optional[str] = None
    chat_id: Optional[str] = None
    prompt: Optional[str] = None
    content: Optional[str] = None
    model_id: Optional[str] = None
    create_time: Optional[str] = None