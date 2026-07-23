# social/schemas/social_schema.py
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ==================== 评论相关 Schema ====================

class CommentSchema(BaseModel):
    """评论响应Schema（驼峰命名）"""
    id: int = Field(..., description="评论ID")
    content: str = Field(..., description="评论内容")
    parent_id: Optional[int] = Field(None, description="父评论ID", alias="parentId")
    top_id: Optional[int] = Field(None, description="顶级评论ID", alias="topId")
    relation_id: int = Field(..., description="关联资源ID", alias="relationId")
    type: str = Field(..., description="资源类型")
    user_id: str = Field(..., description="评论用户ID", alias="userId")
    username: Optional[str] = Field(None, description="评论者昵称")
    avater: Optional[str] = Field(None, description="评论者头像")
    reply_count: int = Field(default=0, description="回复总数", alias="replyCount")
    reply_list: Optional[List["CommentSchema"]] = Field(default=[], description="回复列表", alias="replyList")
    reply_user_name: Optional[str] = Field(None, description="被回复人昵称", alias="replyUserName")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class InsertCommentSchema(BaseModel):
    """新增评论请求Schema"""
    content: str = Field(..., description="评论内容", min_length=1, max_length=500)
    parent_id: int = Field(0, description="父评论ID，一级评论传0", alias="parentId")
    top_id: int = Field(0, description="顶级评论ID，一级评论传0", alias="topId")
    relation_id: int = Field(..., description="关联资源ID", alias="relationId")
    type: str = Field(..., description="资源类型", alias="type")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "content": "这部电影很好看！",
                "parentId": 0,
                "topId": 0,
                "relationId": 1001,
                "type": "movie"
            }
        }
    )


class CommentListResponse(BaseModel):
    """评论列表响应"""
    list: List[CommentSchema] = Field(default=[], description="评论列表")
    total: int = Field(default=0, description="总记录数")


# ==================== 点赞相关 Schema ====================

class LikeSchema(BaseModel):
    """点赞响应Schema（驼峰命名）"""
    id: int = Field(..., description="主键ID")
    relation_id: int = Field(..., description="关联资源ID", alias="relationId")
    type: str = Field(..., description="资源类型")
    user_id: str = Field(..., description="用户ID", alias="userId")
    username: Optional[str] = Field(None, description="用户昵称")
    create_time: Optional[datetime] = Field(None, description="创建时间", alias="createTime")
    update_time: Optional[datetime] = Field(None, description="更新时间", alias="updateTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class LikeRequestSchema(BaseModel):
    """点赞请求Schema"""
    relation_id: int = Field(..., description="关联资源ID", alias="relationId")
    type: str = Field(..., description="资源类型", alias="type")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "relationId": 1001,
                "type": "movie"
            }
        }
    )


# ==================== 查询参数 Schema ====================

class CommentQueryParams(BaseModel):
    """评论查询参数"""
    relation_id: int = Field(..., description="关联资源ID")
    type: str = Field(..., description="资源类型")
    page_num: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")


class ReplyQueryParams(BaseModel):
    """回复查询参数"""
    top_id: int = Field(..., description="顶级评论ID")
    page_num: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")