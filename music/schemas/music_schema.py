# music/schemas/music_schema.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class MusicSchema(BaseModel):
    """音乐对象Schema（响应模型）"""
    id: int = Field(..., description="主键")
    album_id: Optional[int] = Field(None, description="专辑id", alias="albumId")
    song_name: Optional[str] = Field(None, description="歌曲名称", alias="songName")
    author_name: Optional[str] = Field(None, description="作者名称", alias="authorName")
    author_id: Optional[int] = Field(None, description="歌手id", alias="authorId")
    album_name: Optional[str] = Field(None, description="专辑名称", alias="albumName")
    version: Optional[str] = Field(None, description="版本")
    language: Optional[str] = Field(None, description="语言")
    publish_date: Optional[datetime] = Field(None, description="发布日期", alias="publishDate")
    wide_audio_id: Optional[int] = Field(None, description="宽度音频id", alias="wideAudioId")
    is_publish: Optional[int] = Field(None, description="是否发布", alias="isPublish")
    big_pack_id: Optional[int] = Field(None, description="大型集合id", alias="bigPackId")
    final_id: Optional[int] = Field(None, description="最终id", alias="finalId")
    audio_id: Optional[int] = Field(None, description="音频id", alias="audioId")
    similar_audio_id: Optional[int] = Field(None, description="相似的音乐id", alias="similarAudioId")
    is_hot: Optional[int] = Field(None, description="是否热门", alias="isHot")
    album_audio_id: Optional[int] = Field(None, description="歌曲音频id", alias="albumAudioId")
    audio_group_id: Optional[int] = Field(None, description="专辑id", alias="audioGroupId")
    cover: Optional[str] = Field(None, description="歌曲图片")
    play_url: Optional[str] = Field(None, description="网络播放地址", alias="playUrl")
    local_play_url: Optional[str] = Field(None, description="本地播放地址", alias="localPlayUrl")
    source_name: Optional[str] = Field(None, description="播放源", alias="sourceName")
    source_url: Optional[str] = Field(None, description="播放地址", alias="sourceUrl")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")
    label: Optional[str] = Field(None, description="标签")
    lyrics: Optional[str] = Field(None, description="歌词")
    is_like: int = Field(default=0, description="是否点赞：1-已点赞，0-未点赞", alias="isLike")
    times: int = Field(default=0, description="播放次数（暂未实现）")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class MusicQueryParams(BaseModel):
    """音乐查询参数"""
    page_num: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")