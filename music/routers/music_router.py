from datetime import datetime

from fastapi import APIRouter, Depends, Query, Header, HTTPException, Path
from typing import Optional

from common.utils.result_util import ResultEntity
from music.schemas.music_query_schema import MusicQuerySchema
from music.schemas.music_record_schema import InsertMusicRecordSchema
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

# music/routers/music_router.py (追加部分)

@router.get("/getMusicListByAuthorId", response_model=ResultEntity)
async def get_music_list_by_author_id(
        authorId: int = Query(..., description="歌手ID（对应 music 表的 author_id）"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        current_user_id: str = Depends(get_user_id_from_header),
        music_service: MusicService = Depends()
) -> ResultEntity:
    """
    根据歌手ID分页获取音乐列表

    查询该歌手下的所有歌曲，
    并查询当前用户对每首歌曲的点赞状态（is_like）

    Args:
        authorId: 歌手ID
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大100
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 分页音乐列表（包含 isLike 字段）
    """
    return await music_service.get_music_list_by_author_id(
        author_id=authorId,
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )

@router.get("/getFavoriteAuthor", response_model=ResultEntity)
async def get_favorite_author(
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取当前用户喜欢的歌手列表

    根据当前登录用户ID查询歌手收藏表（music_author_like），
    再根据 author_id 关联查询歌手表（music_authors）获取歌手详情

    返回数据包含：
    - 歌手基本信息（id, author_id, author_name, category_id, avatar, type, country, birthday, identity, rank）
    - 不进行分页，返回所有收藏的歌手

    Args:
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 歌手列表（data为数组，total为总数）
    """
    return await music_service.get_favorite_authors(
        user_id=current_user_id
    )

@router.post("/insertFavoriteAuthor/{authorId}", response_model=ResultEntity)
async def insert_favorite_author(
    authorId: int = Path(..., description="歌手ID（关联 music_authors 表的 author_id 字段）"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    添加喜欢的歌手

    将当前用户与指定歌手建立喜欢关联，记录到 music_author_like 表中

    Args:
        authorId: 歌手ID
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 操作结果
            - 成功: data=1, msg="添加喜欢歌手成功"
            - 失败: data=None, msg="错误信息"
    """
    return await music_service.insert_favorite_author(
        user_id=current_user_id,
        author_id=authorId
    )


@router.delete("/deleteFavoriteAuthor/{authorId}", response_model=ResultEntity)
async def delete_favorite_author(
    authorId: int = Path(..., description="歌手ID（关联 music_authors 表的 author_id 字段）"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    取消喜欢的歌手

    删除当前用户与指定歌手的喜欢关联

    Args:
        authorId: 歌手ID
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 操作结果
            - 成功: data=1, msg="取消喜欢歌手成功"
            - 失败: data=None, msg="错误信息"
    """
    return await music_service.delete_favorite_author(
        user_id=current_user_id,
        author_id=authorId
    )

@router.get("/getMusicRecord", response_model=ResultEntity)
async def get_music_record(
    startDate: Optional[datetime] = Query(None, description="开始时间，格式yyyy-MM-dd HH:mm:ss"),
    endDate: Optional[datetime] = Query(None, description="结束时间，格式yyyy-MM-dd HH:mm:ss"),
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取当前用户的音乐播放历史

    按音乐去重，返回每首音乐的最新播放记录和播放总次数

    核心逻辑：
    1. 获取用户指定时间范围内的所有播放记录
    2. 按 music_id 分组，每组取最新的一条记录（MAX(create_time)）
    3. 关联 music 表，获取音乐的完整信息
    4. 统计每首音乐在指定时间范围内的播放总次数（times字段）

    Args:
        startDate: 开始时间（可选）
        endDate: 结束时间（可选）
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大500
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 播放记录列表（包含 times 播放总次数字段）
    """
    return await music_service.get_music_record(
        user_id=current_user_id,
        start_date=startDate,
        end_date=endDate,
        page_num=pageNum,
        page_size=pageSize
    )

@router.post("/insertMusicRecord", response_model=ResultEntity)
async def insert_music_record(
    record_data: InsertMusicRecordSchema,
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    添加音乐播放记录

    用户播放音乐时，记录一条播放历史到 music_record 表

    Args:
        record_data: 播放记录请求参数（musicId, platform, version, device）
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 新增记录的ID
    """
    return await music_service.insert_music_record(
        user_id=current_user_id,
        record_data=record_data
    )

@router.post("/insertMusicLike/{id}", response_model=ResultEntity)
async def insert_music_like(
    id: int = Path(..., description="音乐ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    添加音乐红心收藏

    用户收藏一首音乐，数据写入 music_like 表
    如果已收藏，返回提示信息

    Args:
        id: 音乐ID（路径参数）
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 新增记录ID
    """
    return await music_service.insert_music_like(
        user_id=current_user_id,
        music_id=id
    )

@router.delete("/deleteMusicLike/{id}", response_model=ResultEntity)
async def delete_music_like(
    id: int = Path(..., description="音乐ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    取消音乐红心收藏

    取消用户对某首音乐的收藏

    Args:
        id: 音乐ID（路径参数）
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 操作结果
    """
    return await music_service.delete_music_like(
        user_id=current_user_id,
        music_id=id
    )

@router.get("/getMusicLike", response_model=ResultEntity)
async def get_music_like_list(
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取用户收藏的音乐列表（红心收藏）

    从 music_like 表查询用户所有收藏记录，关联 music 表获取音乐详情
    按收藏时间倒序排列

    Args:
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大500
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 收藏音乐列表
    """
    return await music_service.get_music_like_list(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )

@router.get("/searchMusic", response_model=ResultEntity)
async def search_music(
    keyword: str = Query(..., description="搜索关键词（支持歌曲名、歌手名、专辑名模糊匹配）"),
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    根据关键词搜索音乐

    在 music 表的 song_name、author_name、album_name 三个字段上执行模糊匹配
    返回结果包含当前用户是否已收藏该音乐（isFavorite 字段）

    Args:
        keyword: 搜索关键词
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大500
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 搜索结果列表（包含 isFavorite 字段）
    """
    return await music_service.search_music(
        user_id=current_user_id,
        keyword=keyword,
        page_num=pageNum,
        page_size=pageSize
    )

@router.get("/queryMusic", response_model=ResultEntity)
async def query_music(
    songName: Optional[str] = Query(None, description="歌曲名称（模糊匹配）"),
    authorName: Optional[str] = Query(None, description="歌手名称（模糊匹配）"),
    albumName: Optional[str] = Query(None, description="专辑名称（模糊匹配）"),
    language: Optional[str] = Query(None, description="语言（精确匹配）"),
    publishStart: Optional[datetime] = Query(None, description="发布日期起始（>=），格式yyyy-MM-dd"),
    label: Optional[str] = Query(None, description="标签（模糊匹配）"),
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    多条件查询音乐列表

    支持按歌曲名、歌手名、专辑名、语言、发布日期起始、标签进行组合查询
    所有条件均为可选，返回结果包含当前用户是否已收藏该音乐（isFavorite 字段）

    Args:
        songName: 歌曲名称（模糊匹配）
        authorName: 歌手名称（模糊匹配）
        albumName: 专辑名称（模糊匹配）
        language: 语言（精确匹配）
        publishStart: 发布日期起始（>=）
        label: 标签（模糊匹配）
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大500
        current_user_id: 当前登录用户ID（由网关透传）
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 符合条件的音乐列表（包含 isFavorite 字段）
    """
    # 构建查询参数对象
    query_params = MusicQuerySchema(
        songName=songName,
        authorName=authorName,
        albumName=albumName,
        language=language,
        publishStart=publishStart,
        label=label,
        pageNum=pageNum,
        pageSize=pageSize
    )

    return await music_service.query_music(
        user_id=current_user_id,
        query_params=query_params
    )

@router.get("/getMusicAuthorCategory", response_model=ResultEntity)
async def get_music_author_category(
    music_service: MusicService = Depends()
) -> ResultEntity:
    """
    获取歌手分类列表

    获取所有可用的歌手分类，用于前端展示歌手分类导航
    只返回 disabled = 0 的分类，按 rank 降序排列

    Args:
        music_service: 音乐服务实例

    Returns:
        ResultEntity: 歌手分类列表
    """
    return await music_service.get_author_category_list()
