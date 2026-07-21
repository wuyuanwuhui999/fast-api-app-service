from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class InsertMusicRecordSchema(BaseModel):
    """插入音乐播放记录请求Schema"""
    musicId: int = Field(..., description="音乐ID", alias="musicId")
    platform: Optional[str] = Field(None, description="播放平台（iOS/Android/Web等）")
    version: Optional[str] = Field(None, description="App版本号")
    device: Optional[str] = Field(None, description="设备型号")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "musicId": 1001,
                "platform": "Android",
                "version": "2.5.1",
                "device": "Xiaomi11"
            }
        }
    )


class MusicRecordResponseSchema(BaseModel):
    """音乐播放记录响应Schema"""
    id: int = Field(..., description="记录ID")
    music_id: int = Field(..., description="音乐ID")
    user_id: str = Field(..., description="用户ID")
    platform: Optional[str] = Field(None, description="播放平台")
    version: Optional[str] = Field(None, description="App版本号")
    device: Optional[str] = Field(None, description="设备型号")
    create_time: Optional[datetime] = Field(None, description="创建时间")
    update_time: Optional[datetime] = Field(None, description="更新时间")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )