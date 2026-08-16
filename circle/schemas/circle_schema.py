# circle/schemas/circle_schema.py
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class InsertCircleSchema(BaseModel):
    """新增朋友圈（电影圈/音乐圈）请求Schema"""
    content: Optional[str] = Field(None, description="朋友圈内容")
    imgs: Optional[str] = Field(None, description="朋友圈图片（base64，多张用逗号隔开）")
    relation_id: Optional[int] = Field(None, description="关联音乐audio_id或者电影movie_id", alias="relationId")
    type: Optional[str] = Field(None, description="类型（MUSIC/MOVIE）")
    permission: int = Field(1, description="权限，0不公开，1公开")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "content": "这部电影很好看！",
                "imgs": "data:image/png;base64,xxxx",
                "relationId": 1001,
                "type": "MOVIE",
                "permission": 1
            }
        }
    )


class LikeSchema(BaseModel):
    """点赞响应Schema（驼峰命名）"""
    id: int = Field(..., description="主键ID")
    type: Optional[str] = Field(None, description="资源类型")
    user_id: Optional[str] = Field(None, description="用户ID", alias="userId")
    username: Optional[str] = Field(None, description="用户昵称")
    relation_id: Optional[int] = Field(None, description="关联资源ID", alias="relationId")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CommentSchema(BaseModel):
    """评论响应Schema（驼峰命名）"""
    id: int = Field(..., description="主键ID")
    content: Optional[str] = Field(None, description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论ID", alias="parentId")
    top_id: Optional[int] = Field(None, description="顶级评论ID", alias="topId")
    relation_id: Optional[int] = Field(None, description="关联资源ID", alias="relationId")
    type: Optional[str] = Field(None, description="资源类型")
    user_id: Optional[str] = Field(None, description="评论用户ID", alias="userId")
    username: Optional[str] = Field(None, description="评论者昵称")
    avater: Optional[str] = Field(None, description="评论者头像")
    reply_user_id: Optional[str] = Field(None, description="被回复者ID", alias="replyUserId")
    reply_user_name: Optional[str] = Field(None, description="被回复者昵称", alias="replyUserName")
    reply_count: Optional[int] = Field(0, description="回复总数", alias="replyCount")
    reply_list: Optional[List["CommentSchema"]] = Field(default_factory=list, description="回复列表", alias="replyList")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CircleSchema(BaseModel):
    """朋友圈响应Schema（驼峰命名）"""
    id: int = Field(..., description="主键ID")
    relation_id: Optional[int] = Field(None, description="关联音乐或电影ID", alias="relationId")
    content: Optional[str] = Field(None, description="朋友圈内容")
    imgs: Optional[str] = Field(None, description="朋友圈图片")
    type: Optional[str] = Field(None, description="类型")
    user_id: Optional[str] = Field(None, description="用户ID", alias="userId")
    username: Optional[str] = Field(None, description="用户昵称")
    useravater: Optional[str] = Field(None, description="用户头像")
    permission: Optional[int] = Field(None, description="权限")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")
    music_song_name: Optional[str] = Field(None, description="歌曲名称", alias="musicSongName")
    music_audio_id: Optional[Any] = Field(None, description="歌曲id", alias="musicAudioId")
    music_author_name: Optional[str] = Field(None, description="歌曲作者", alias="musicAuthorName")
    music_album_name: Optional[str] = Field(None, description="专辑名称", alias="musicAlbumName")
    music_cover: Optional[str] = Field(None, description="音乐图片", alias="musicCover")
    music_play_url: Optional[str] = Field(None, description="音乐播放地址", alias="musicPlayUrl")
    music_local_play_url: Optional[str] = Field(None, description="音乐本地播放地址", alias="musicLocalPlayUrl")
    music_lyrics: Optional[str] = Field(None, description="歌词", alias="musicLyrics")
    movie_id: Optional[Any] = Field(None, description="电影id", alias="movieId")
    movie_name: Optional[str] = Field(None, description="电影名称", alias="movieName")
    movie_director: Optional[str] = Field(None, description="电影导演", alias="movieDirector")
    movie_star: Optional[str] = Field(None, description="电影主演", alias="movieStar")
    movie_type: Optional[str] = Field(None, description="电影类型", alias="movieType")
    movie_country_language: Optional[str] = Field(None, description="电影上映国家", alias="movieCountryLanguage")
    movie_viewing_state: Optional[str] = Field(None, description="电影状态", alias="movieViewingState")
    movie_release_time: Optional[str] = Field(None, description="上映时间", alias="movieReleaseTime")
    movie_img: Optional[str] = Field(None, description="电影海报", alias="movieImg")
    movie_classify: Optional[str] = Field(None, description="电影分类", alias="movieClassify")
    movie_local_img: Optional[str] = Field(None, description="电影本地图片", alias="movieLocalImg")
    movie_score: Optional[str] = Field(None, description="电影得分", alias="movieScore")
    circle_likes: Optional[List[LikeSchema]] = Field(default_factory=list, description="点赞列表", alias="circleLikes")
    circle_comments: Optional[List[CommentSchema]] = Field(default_factory=list, description="评论列表", alias="circleComments")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
