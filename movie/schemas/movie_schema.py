# movie/schemas/movie_schema.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MovieSchema(BaseModel):
    """电影对象Schema（响应模型）"""
    id: int = Field(..., description="主键")
    movie_id: Optional[int] = Field(None, description="电影id", alias="movieId")
    director: Optional[str] = Field(None, description="导演")
    star: Optional[str] = Field(None, description="主演")
    type: Optional[str] = Field(None, description="类型")
    country_language: Optional[str] = Field(None, description="国家/语言", alias="countryLanguage")
    viewing_state: Optional[str] = Field(None, description="观看状态", alias="viewingState")
    release_time: Optional[str] = Field(None, description="上映时间", alias="releaseTime")
    plot: Optional[str] = Field(None, description="剧情")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")
    movie_name: Optional[str] = Field(None, description="电影名称", alias="movieName")
    is_recommend: Optional[str] = Field(None, description="是否推荐", alias="isRecommend")
    img: Optional[str] = Field(None, description="电影海报")
    classify: Optional[str] = Field(None, description="分类")
    source_name: Optional[str] = Field(None, description="来源名称", alias="sourceName")
    source_url: Optional[str] = Field(None, description="来源地址", alias="sourceUrl")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    local_img: Optional[str] = Field(None, description="本地图片", alias="localImg")
    label: Optional[str] = Field(None, description="播放集数/标签")
    original_href: Optional[str] = Field(None, description="源地址", alias="originalHref")
    description: Optional[str] = Field(None, description="简单描述")
    target_href: Optional[str] = Field(None, description="链接地址", alias="targetHref")
    use_status: Optional[str] = Field(None, description="使用状态", alias="useStatus")
    score: Optional[float] = Field(None, description="评分")
    category: Optional[str] = Field(None, description="类目")
    ranks: Optional[str] = Field(None, description="排名")
    douban_url: Optional[str] = Field(None, description="豆瓣网url", alias="doubanUrl")
    duration: Optional[int] = Field(None, description="播放时长")
    privilege_id: Optional[int] = Field(None, description="观看权限", alias="privilegeId")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class MovieStarSchema(BaseModel):
    """电影演员Schema"""
    id: int = Field(..., description="主键")
    star_name: Optional[str] = Field(None, description="演员名称", alias="starName")
    img: Optional[str] = Field(None, description="演员图片地址")
    local_img: Optional[str] = Field(None, description="本地图片", alias="localImg")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")
    movie_id: Optional[str] = Field(None, description="电影id", alias="movieId")
    role: Optional[str] = Field(None, description="角色")
    href: Optional[str] = Field(None, description="演员的豆瓣链接地址")
    works: Optional[str] = Field(None, description="代表作")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class MovieUrlSchema(BaseModel):
    """电影播放地址Schema"""
    id: int = Field(..., description="主键")
    movie_name: Optional[str] = Field(None, description="电影名称", alias="movieName")
    movie_id: Optional[int] = Field(None, description="对应电影的id", alias="movieId")
    href: Optional[str] = Field(None, description="源地址")
    label: Optional[str] = Field(None, description="集数")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")
    url: Optional[str] = Field(None, description="播放地址")
    play_group: Optional[str] = Field(None, description="播放分组", alias="playGroup")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class SearchHistorySchema(BaseModel):
    """搜索历史Schema"""
    id: int = Field(..., description="主键")
    user_id: Optional[str] = Field(None, description="用户ID", alias="userId")
    type: Optional[str] = Field(None, description="搜索类型")
    keyword: Optional[str] = Field(None, description="搜索关键词")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class MovieSearchParams(BaseModel):
    """电影搜索参数"""
    classify: Optional[str] = Field(None, description="分类")
    category: Optional[str] = Field(None, description="类目")
    label: Optional[str] = Field(None, description="标签")
    star: Optional[str] = Field(None, description="主演")
    director: Optional[str] = Field(None, description="导演")
    keyword: Optional[str] = Field(None, description="关键词")
    page_num: int = Field(default=1, ge=1, description="页码", alias="pageNum")
    page_size: int = Field(default=20, ge=1, le=500, description="每页数量", alias="pageSize")
