# music/routers/music_router.py
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from typing import Optional

from common.utils.result_util import ResultEntity
from music.services.music_service import MusicService

router = APIRouter(
    prefix="/service/music",
    tags=["music"],
    responses={404: {"description": "Not found"}}
)


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/keywordMusic", response_model=ResultEntity)
async def get_recommend_music(
        page_num: int = Query(1, ge=1, description="页码，从1开始"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        current_user_id: str = Depends(get_user_id_from_header),
        music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取推荐音乐列表

    按 is_hot 降序排序，支持分页
    关联查询当前用户的点赞状态（is_like字段）

    Args:
        page_num: 页码，从1开始
        page_size: 每页数量，最大100
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 音乐列表（包含 is_like 字段）
    """
    return await music_service.get_recommend_music(
        user_id=current_user_id,
        page_num=page_num,
        page_size=page_size
    )