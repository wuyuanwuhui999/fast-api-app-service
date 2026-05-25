from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class AgentParamsEntity(BaseModel):
    """WebSocket消息参数 - 通过send方法传递"""
    prompt: str = Field(..., description="用户输入的提示词")
    directoryId: str = Field(default="default", description="目录ID")
    chatId: str = Field(..., description="会话ID")
    modelId: str = Field(..., description="模型ID")
    showThink: bool = Field(default=False, description="是否显示思考过程")
    tenant_id: Optional[str] = Field(default=None, description="租户ID")


class MusicSchema(BaseModel):
    """音乐数据Schema"""
    id: Optional[int] = None
    song_name: Optional[str] = None
    author_name: Optional[str] = None
    album_name: Optional[str] = None
    cover: Optional[str] = None
    play_url: Optional[str] = None
    label: Optional[str] = None
    is_like: int = Field(default=0, description="是否点赞：0-未点赞，1-已点赞")
    is_favorite: int = Field(default=0, description="是否收藏：0-未收藏，1-已收藏")


class ChatHistorySchema(BaseModel):
    """聊天历史记录Schema"""
    id: Optional[int] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    model_id: Optional[str] = None
    files: Optional[str] = None
    chat_id: Optional[str] = None
    prompt: Optional[str] = None
    system_prompt: Optional[str] = None
    think_content: Optional[str] = None
    response_content: Optional[str] = None
    content: Optional[str] = None
    create_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class ChatModelSchema(BaseModel):
    """模型配置Schema"""
    id: str
    type: str
    api_key: Optional[str] = None
    model_name: str
    base_url: Optional[str] = None
    disabled: int = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )