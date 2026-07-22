from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MusicQuerySchema(BaseModel):
    """音乐多条件查询请求Schema"""
    songName: Optional[str] = Field(None, description="歌曲名称（模糊匹配）", alias="songName")
    authorName: Optional[str] = Field(None, description="歌手名称（模糊匹配）", alias="authorName")
    albumName: Optional[str] = Field(None, description="专辑名称（模糊匹配）", alias="albumName")
    language: Optional[str] = Field(None, description="语言（精确匹配）")
    publishStart: Optional[datetime] = Field(None, description="发布日期起始（>=）", alias="publishStart")
    label: Optional[str] = Field(None, description="标签（模糊匹配）")
    pageNum: int = Field(1, ge=1, description="页码，从1开始", alias="pageNum")
    pageSize: int = Field(20, ge=1, le=500, description="每页数量，最大500", alias="pageSize")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "songName": "七里香",
                "authorName": "周杰伦",
                "albumName": "七里香",
                "language": "国语",
                "publishStart": "2025-01-01",
                "label": "流行",
                "pageNum": 1,
                "pageSize": 20
            }
        }
    )