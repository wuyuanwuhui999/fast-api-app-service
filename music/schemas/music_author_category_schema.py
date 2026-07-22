# music/schemas/music_author_category_schema.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MusicAuthorCategorySchema(BaseModel):
    """歌手分类响应Schema（驼峰命名）"""
    id: int = Field(..., description="主键")
    category_name: str = Field(..., description="分类名称", alias="categoryName")
    rank: Optional[int] = Field(0, description="排序权重，数值越大越靠前")
    disabled: Optional[int] = Field(0, description="是否禁用：0-启用，1-禁用")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 模型创建
        populate_by_name=True,  # 允许使用字段名或别名
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )