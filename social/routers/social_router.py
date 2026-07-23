# social/routers/social_router.py
from typing import Optional
from fastapi import APIRouter, Depends, Query, Header, HTTPException, Path, Body

from common.utils.result_util import ResultEntity
from social.services.social_service import SocialService
from social.schemas.social_schema import InsertCommentSchema, LikeRequestSchema

router = APIRouter(
    prefix="/service/social",
    tags=["social"],
    responses={404: {"description": "Not found"}}
)


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


# ==================== 评论接口 ====================

@router.get("/getCommentCount", response_model=ResultEntity)
async def get_comment_count(
        relationId: int = Query(..., description="关联资源ID"),
        type: str = Query(..., description="资源类型（movie/article/music等）"),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    获取评论总数
    """
    return await social_service.get_comment_count(relationId, type)


@router.get("/getTopCommentList", response_model=ResultEntity)
async def get_top_comment_list(
        relationId: int = Query(..., description="关联资源ID"),
        type: str = Query(..., description="资源类型（movie/article/music等）"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    获取一级评论列表（根评论）
    返回每条评论及其前5条回复和回复总数
    """
    return await social_service.get_top_comment_list(
        relation_id=relationId,
        type=type,
        page_num=pageNum,
        page_size=pageSize
    )


@router.get("/getReplyCommentList", response_model=ResultEntity)
async def get_reply_comment_list(
        topId: int = Query(..., description="顶级评论ID"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    获取回复列表（二级评论）
    分页获取某个顶级评论下的所有回复
    """
    return await social_service.get_reply_comment_list(
        top_id=topId,
        page_num=pageNum,
        page_size=pageSize
    )


@router.post("/insertComment", response_model=ResultEntity)
async def insert_comment(
        comment_data: InsertCommentSchema = Body(..., description="评论请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    新增评论/回复

    - parentId=0, topId=0：发表一级评论
    - parentId>0, topId>0：发表回复（被回复的评论ID作为parentId，顶级评论ID作为topId）
    """
    return await social_service.insert_comment(comment_data, current_user_id)


@router.delete("/deleteComment/{id}", response_model=ResultEntity)
async def delete_comment(
        id: int = Path(..., description="评论ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    删除评论（仅限评论所有者）
    """
    return await social_service.delete_comment(id, current_user_id)


# ==================== 点赞接口 ====================

@router.post("/saveLike", response_model=ResultEntity)
async def save_like(
        like_data: LikeRequestSchema = Body(..., description="点赞请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    添加点赞/收藏
    幂等操作，重复请求不会重复插入
    """
    return await social_service.save_like(like_data, current_user_id)


@router.delete("/deleteLike", response_model=ResultEntity)
async def delete_like(
        relationId: int = Query(..., description="关联资源ID"),
        type: str = Query(..., description="资源类型"),
        current_user_id: str = Depends(get_user_id_from_header),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    取消点赞/收藏
    """
    return await social_service.delete_like(relationId, type, current_user_id)


@router.get("/isLike", response_model=ResultEntity)
async def is_like(
        relationId: int = Query(..., description="关联资源ID"),
        type: str = Query(..., description="资源类型"),
        current_user_id: str = Depends(get_user_id_from_header),
        social_service: SocialService = Depends()
) -> ResultEntity:
    """
    检查是否已点赞
    返回 data=1 表示已点赞，data=0 表示未点赞
    """
    return await social_service.is_like(relationId, type, current_user_id)