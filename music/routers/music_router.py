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


@router.get("/getKeywordMusic", response_model=ResultEntity)
async def get_keyword_music(
        current_user_id: str = Depends(get_user_id_from_header),
        music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取搜索框中推荐的一首音乐（热门优先）

    按 is_hot 降序取第一条音乐数据，用于搜索框推荐展示
    关联查询当前用户的点赞状态（is_like字段）

    Args:
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 单首音乐数据（包含 is_like 字段），如果无数据则返回失败
    """
    return await music_service.get_keyword_music(
        user_id=current_user_id
    )