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

# music/routers/music_router.py (追加部分)


@router.get("/getMusicClassify", response_model=ResultEntity)
async def get_music_classify(
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取音乐分类列表

    按 classify_rank 降序排列，只返回 disabled=0 且 permission >= 0 的记录

    Args:
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 分类列表
    """
    return await music_service.get_music_classify()

@router.get("/getMusicListByClassifyId", response_model=ResultEntity)
async def get_music_list_by_classify_id(
        classifyId: int = Query(..., description="分类ID"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        current_user_id: str = Depends(get_user_id_from_header),
        music_service: MusicService = Depends()
) -> ResultEntity:
    """
    根据分类ID分页获取音乐列表

    从分类关联表 music_classify 中查询该分类下的所有音乐ID，
    关联 music 表获取音乐详情，
    并查询当前用户对每首音乐的点赞状态（is_like）

    Args:
        classifyId: 分类ID
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大100
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 分页音乐列表（包含 isLike 字段）
    """
    return await music_service.get_music_list_by_classify_id(
        classify_id=classifyId,
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )

@router.get("/getMusicAuthorListByCategoryId", response_model=ResultEntity)
async def get_music_author_list_by_category_id(
        categoryId: int = Query(..., description="分类ID"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        current_user_id: str = Depends(get_user_id_from_header),
        music_service: MusicService = Depends()
) -> ResultEntity:
    """
    根据分类ID分页获取歌手列表

    从 music_authors 表中查询该分类下的所有歌手，
    统计每个歌手在 music 表中的歌曲数量，
    并查询当前用户对每个歌手的点赞状态（is_like）

    Args:
        categoryId: 分类ID
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大100
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 分页歌手列表
    """
    return await music_service.get_author_list_by_category_id(
        category_id=categoryId,
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )