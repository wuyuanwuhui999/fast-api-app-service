# movie/routers/movie_router.py
from typing import Optional

from fastapi import APIRouter, Depends, Query, Header, HTTPException, Path

from common.utils.result_util import ResultEntity
from movie.services.movie_service import MovieService

router = APIRouter(
    prefix="/service/movie",
    tags=["movie"],
    responses={404: {"description": "Not found"}}
)


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


# ==================== 分类 & 推荐 ====================

@router.get("/findClassify", response_model=ResultEntity)
async def find_classify(
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取电影分类列表"""
    return await movie_service.find_classify()


@router.get("/getKeyWord", response_model=ResultEntity)
async def get_keyword(
    classify: str = Query(..., description="分类（如：电影、电视剧）"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """按照类型获取推荐影片"""
    return await movie_service.get_keyword(classify=classify)


@router.get("/getUserMsg", response_model=ResultEntity)
async def get_user_msg(
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """查询当前用户的使用天数、关注数、观看记录数、浏览记录数"""
    return await movie_service.get_user_msg(user_id=current_user_id)


# ==================== 分类 & 类目 ====================

@router.get("/getAllCategoryByClassify", response_model=ResultEntity)
async def get_all_category_by_classify(
    classify: str = Query(..., description="分类大类（如：电影）"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """按classify大类查询所有category小类"""
    return await movie_service.get_all_category_by_classify(classify=classify)


@router.get("/getAllCategoryListByPageName", response_model=ResultEntity)
async def get_all_category_list_by_page_name(
    pageName: str = Query(..., description="页面名称"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """按页面获取要展示的category小类"""
    return await movie_service.get_all_category_list_by_page_name(page_name=pageName)


@router.get("/getCategoryList", response_model=ResultEntity)
async def get_category_list(
    classify: str = Query(..., description="分类"),
    category: str = Query(..., description="类目"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取大类中的小类"""
    return await movie_service.get_category_list(classify=classify, category=category)


@router.get("/getTopMovieList", response_model=ResultEntity)
async def get_top_movie_list(
    classify: str = Query(..., description="分类"),
    category: Optional[str] = Query(None, description="类目（可选）"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """根据分类获取前20条数据"""
    return await movie_service.get_top_movie_list(classify=classify, category=category)


# ==================== 搜索 ====================

@router.get("/search", response_model=ResultEntity)
async def search(
    classify: Optional[str] = Query(None, description="分类"),
    category: Optional[str] = Query(None, description="类目"),
    label: Optional[str] = Query(None, description="标签"),
    star: Optional[str] = Query(None, description="主演"),
    director: Optional[str] = Query(None, description="导演"),
    keyword: Optional[str] = Query(None, description="关键词"),
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """搜索电影（支持多条件分页）"""
    return await movie_service.search(
        classify=classify,
        category=category,
        label=label,
        star=star,
        director=director,
        keyword=keyword,
        page_num=pageNum,
        page_size=pageSize
    )


# ==================== 演员 & 播放地址 ====================

@router.get("/getStar/{movieId}", response_model=ResultEntity)
async def get_star(
    movieId: int = Path(..., description="电影ID"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取演员列表"""
    return await movie_service.get_star(movie_id=movieId)


@router.get("/getMovieUrl", response_model=ResultEntity)
async def get_movie_url(
    movieId: int = Query(..., description="电影ID"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取播放地址"""
    return await movie_service.get_movie_url(movie_id=movieId)


# ==================== 播放记录 ====================

@router.get("/getPlayRecord", response_model=ResultEntity)
async def get_play_record(
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取播放记录"""
    return await movie_service.get_play_record(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )


@router.post("/savePlayRecord/{movieId}", response_model=ResultEntity)
async def save_play_record(
    movieId: int = Path(..., description="电影ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """保存播放记录"""
    return await movie_service.save_play_record(
        movie_id=movieId,
        user_id=current_user_id
    )


# ==================== 浏览记录 ====================

@router.get("/getViewRecord", response_model=ResultEntity)
async def get_view_record(
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取浏览记录"""
    return await movie_service.get_view_record(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )


@router.post("/saveViewRecord/{movieId}", response_model=ResultEntity)
async def save_view_record(
    movieId: int = Path(..., description="电影ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """保存浏览记录"""
    return await movie_service.save_view_record(
        movie_id=movieId,
        user_id=current_user_id
    )


# ==================== 收藏 ====================

@router.get("/getFavoriteList", response_model=ResultEntity)
async def get_favorite_list(
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取收藏列表"""
    return await movie_service.get_favorite_list(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )


@router.post("/saveFavorite/{movieId}", response_model=ResultEntity)
async def save_favorite(
    movieId: int = Path(..., description="电影ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """添加收藏"""
    return await movie_service.save_favorite(
        movie_id=movieId,
        user_id=current_user_id
    )


@router.delete("/deleteFavorite/{movieId}", response_model=ResultEntity)
async def delete_favorite(
    movieId: int = Path(..., description="电影ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """删除收藏"""
    return await movie_service.delete_favorite(
        movie_id=movieId,
        user_id=current_user_id
    )


@router.get("/isFavorite", response_model=ResultEntity)
async def is_favorite(
    movieId: int = Query(..., description="电影ID"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """查询是否已经收藏"""
    return await movie_service.is_favorite(
        movie_id=movieId,
        user_id=current_user_id
    )


# ==================== 推荐相关 ====================

@router.get("/getYourLikes", response_model=ResultEntity)
async def get_your_likes(
    labels: str = Query(..., description="标签，多个用/分隔"),
    classify: str = Query(..., description="分类"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取猜你想看的电影"""
    return await movie_service.get_your_likes(labels=labels, classify=classify)


@router.get("/getRecommend", response_model=ResultEntity)
async def get_recommend(
    classify: str = Query(..., description="分类"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取推荐的电影"""
    return await movie_service.get_recommend(classify=classify)


# ==================== 电影详情 & 类型相似 ====================

@router.get("/getMovieDetail/{movieId}", response_model=ResultEntity)
async def get_movie_detail(
    movieId: int = Path(..., description="电影ID"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取电影详情"""
    return await movie_service.get_movie_detail(movie_id=movieId)


@router.get("/getMovieListByType", response_model=ResultEntity)
async def get_movie_list_by_type(
    types: str = Query(..., description="类型，多个用空格分隔"),
    classify: str = Query(..., description="分类"),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取类型相似的电影"""
    return await movie_service.get_movie_list_by_type(types=types, classify=classify)


# ==================== 搜索历史 ====================

@router.get("/getSearchHistory", response_model=ResultEntity)
async def get_search_history(
    pageNum: int = Query(1, ge=1, description="页码，从1开始"),
    pageSize: int = Query(20, ge=1, le=500, description="每页数量，最大500"),
    current_user_id: str = Depends(get_user_id_from_header),
    movie_service: MovieService = Depends()
) -> ResultEntity:
    """获取搜索历史"""
    return await movie_service.get_search_history(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )
