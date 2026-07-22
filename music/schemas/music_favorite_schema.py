# music/schemas/music_favorite_schema.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MusicFavoriteDirectorySchema(BaseModel):
    """音乐收藏夹响应Schema"""
    id: int = Field(..., description="收藏夹ID")
    name: str = Field(..., description="收藏夹名称")
    total: int = Field(0, description="收藏夹内音乐总数")
    checked: int = Field(0, description="当前音乐是否在该收藏夹中：1-是，0-否")
    cover: Optional[str] = Field(None, description="收藏夹封面图（取最新添加的音乐封面）")
    createTime: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    updateTime: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class FavoriteDirectoryCreateSchema(BaseModel):
    """创建收藏夹请求Schema"""
    name: str = Field(..., description="收藏夹名称", min_length=1, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "我的最爱"
            }
        }
    )


class FavoriteDirectoryUpdateSchema(BaseModel):
    """更新收藏夹名称请求Schema"""
    id: int = Field(..., description="收藏夹ID")
    name: str = Field(..., description="新的收藏夹名称", min_length=1, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "珍藏金曲"
            }
        }
    )