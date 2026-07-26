# movie/services/movie_service.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from movie.repositories.movie_repository import MovieRepository


class MovieService:
    """电影服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.movie_repository = MovieRepository(db)

    async def find_classify(self) -> ResultEntity:
        """查询电影分类"""
        try:
            data = self.movie_repository.find_classify()
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"查询电影分类失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询电影分类失败: {str(e)}")

    async def get_keyword(self, classify: str) -> ResultEntity:
        """获取推荐的电影"""
        try:
            if not classify:
                return ResultUtil.fail(data=None, msg="分类不能为空")
            data = self.movie_repository.get_keyword(classify)
            if not data:
                return ResultUtil.fail(data=None, msg="暂无推荐电影")
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取推荐电影失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取推荐电影失败: {str(e)}")

    async def get_user_msg(self, user_id: str) -> ResultEntity:
        """获取用户信息（使用天数、各记录数）"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            data = self.movie_repository.get_user_msg(user_id)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取用户信息失败: {str(e)}")

    async def get_all_category_by_classify(self, classify: str) -> ResultEntity:
        """按classify大类查询所有category小类"""
        try:
            if not classify:
                return ResultUtil.fail(data=None, msg="分类不能为空")
            data = self.movie_repository.get_all_category_by_classify(classify)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"按classify查询category失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询失败: {str(e)}")

    async def get_all_category_list_by_page_name(self, page_name: str) -> ResultEntity:
        """按页面获取要展示的category小类"""
        try:
            if not page_name:
                return ResultUtil.fail(data=None, msg="页面名称不能为空")
            data = self.movie_repository.get_all_category_list_by_page_name(page_name)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"按页面查询category失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询失败: {str(e)}")

    async def get_category_list(self, classify: str, category: str) -> ResultEntity:
        """获取大类中的小类"""
        try:
            if not classify or not category:
                return ResultUtil.fail(data=None, msg="参数不完整")
            data, total = self.movie_repository.get_category_list(classify, category)
            return ResultUtil.success(data=data, total=total)
        except Exception as e:
            logger.error(f"获取category列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询失败: {str(e)}")

    async def get_top_movie_list(self, classify: str, category: Optional[str] = None) -> ResultEntity:
        """根据分类获取前20条数据"""
        try:
            if not classify:
                return ResultUtil.fail(data=None, msg="分类不能为空")
            data = self.movie_repository.get_top_movie_list(classify, category)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取Top电影列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询失败: {str(e)}")

    async def search(
        self,
        classify: Optional[str],
        category: Optional[str],
        label: Optional[str],
        star: Optional[str],
        director: Optional[str],
        keyword: Optional[str],
        page_num: int,
        page_size: int
    ) -> ResultEntity:
        """搜索电影"""
        try:
            if page_size > 500:
                page_size = 500
            start = (page_num - 1) * page_size

            data = self.movie_repository.search(
                classify, category, label, star, director, keyword, start, page_size
            )
            total = self.movie_repository.search_total(
                classify, category, label, star, director, keyword
            )
            return ResultUtil.success(data=data, total=total)
        except Exception as e:
            logger.error(f"搜索电影失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"搜索失败: {str(e)}")

    async def get_star(self, movie_id: int) -> ResultEntity:
        """获取电影演员列表"""
        try:
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            data = self.movie_repository.get_star(movie_id)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取演员列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取演员列表失败: {str(e)}")

    async def get_movie_url(self, movie_id: int) -> ResultEntity:
        """获取电影播放地址"""
        try:
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            data = self.movie_repository.get_movie_url(movie_id)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取播放地址失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取播放地址失败: {str(e)}")

    # ==================== 播放记录 ====================

    async def get_play_record(self, user_id: str, page_num: int, page_size: int) -> ResultEntity:
        """获取播放记录"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if page_size > 500:
                page_size = 500
            start = (page_num - 1) * page_size
            data = self.movie_repository.get_play_record(user_id, start, page_size)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取播放记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取播放记录失败: {str(e)}")

    async def save_play_record(self, movie_id: int, user_id: str) -> ResultEntity:
        """保存播放记录"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            result = self.movie_repository.save_play_record(movie_id, user_id)
            if result:
                return ResultUtil.success(data=result, msg="保存成功")
            return ResultUtil.fail(data=None, msg="保存失败")
        except Exception as e:
            logger.error(f"保存播放记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"保存播放记录失败: {str(e)}")

    # ==================== 浏览记录 ====================

    async def get_view_record(self, user_id: str, page_num: int, page_size: int) -> ResultEntity:
        """获取浏览记录"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if page_size > 500:
                page_size = 500
            start = (page_num - 1) * page_size
            data = self.movie_repository.get_view_record(user_id, start, page_size)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取浏览记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取浏览记录失败: {str(e)}")

    async def save_view_record(self, movie_id: int, user_id: str) -> ResultEntity:
        """保存浏览记录"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            result = self.movie_repository.save_view_record(movie_id, user_id)
            if result:
                return ResultUtil.success(data=result, msg="保存成功")
            return ResultUtil.fail(data=None, msg="保存失败")
        except Exception as e:
            logger.error(f"保存浏览记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"保存浏览记录失败: {str(e)}")

    # ==================== 收藏 ====================

    async def get_favorite_list(self, user_id: str, page_num: int, page_size: int) -> ResultEntity:
        """获取收藏列表"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if page_size > 500:
                page_size = 500
            start = (page_num - 1) * page_size
            data = self.movie_repository.get_favorite_list(user_id, start, page_size)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取收藏列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取收藏列表失败: {str(e)}")

    async def save_favorite(self, movie_id: int, user_id: str) -> ResultEntity:
        """添加收藏"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            result = self.movie_repository.save_favorite(movie_id, user_id)
            if result:
                return ResultUtil.success(data=result, msg="收藏成功")
            return ResultUtil.fail(data=None, msg="收藏失败")
        except Exception as e:
            logger.error(f"添加收藏失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"添加收藏失败: {str(e)}")

    async def delete_favorite(self, movie_id: int, user_id: str) -> ResultEntity:
        """删除收藏"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            success = self.movie_repository.delete_favorite(movie_id, user_id)
            if success:
                return ResultUtil.success(data=1, msg="删除成功")
            return ResultUtil.fail(data=None, msg="删除失败或收藏不存在")
        except Exception as e:
            logger.error(f"删除收藏失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"删除收藏失败: {str(e)}")

    async def is_favorite(self, movie_id: int, user_id: str) -> ResultEntity:
        """查询是否已收藏"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            is_fav = self.movie_repository.is_favorite(movie_id, user_id)
            return ResultUtil.success(data=is_fav)
        except Exception as e:
            logger.error(f"查询收藏状态失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"查询收藏状态失败: {str(e)}")

    # ==================== 推荐 ====================

    async def get_your_likes(self, labels: str, classify: str) -> ResultEntity:
        """猜你喜欢"""
        try:
            if not labels or not classify:
                return ResultUtil.fail(data=None, msg="参数不完整")
            labels = labels.strip("/")
            my_labels = labels.split("/") if labels else []
            data = self.movie_repository.get_your_likes(my_labels, classify)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取猜你喜欢失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取猜你喜欢失败: {str(e)}")

    async def get_recommend(self, classify: str) -> ResultEntity:
        """获取推荐电影"""
        try:
            if not classify:
                return ResultUtil.fail(data=None, msg="分类不能为空")
            data = self.movie_repository.get_recommend(classify)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取推荐电影失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取推荐电影失败: {str(e)}")

    # ==================== 电影详情 ====================

    async def get_movie_detail(self, movie_id: int) -> ResultEntity:
        """获取电影详情"""
        try:
            if not movie_id or movie_id <= 0:
                return ResultUtil.fail(data=None, msg="电影ID不能为空")
            data = self.movie_repository.get_movie_detail(movie_id)
            if not data:
                return ResultUtil.fail(data=None, msg="电影不存在")
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取电影详情失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取电影详情失败: {str(e)}")

    async def get_movie_list_by_type(self, types: str, classify: str) -> ResultEntity:
        """按类型获取相似电影"""
        try:
            if not types or not classify:
                return ResultUtil.fail(data=None, msg="参数不完整")
            my_types = types.split(" ")
            data = self.movie_repository.get_movie_list_by_type(my_types, classify)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"按类型获取电影失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"按类型获取电影失败: {str(e)}")

    async def get_search_history(self, user_id: str, page_num: int, page_size: int) -> ResultEntity:
        """获取搜索历史"""
        try:
            if not user_id:
                return ResultUtil.fail(data=None, msg="用户ID不能为空")
            if page_size > 500:
                page_size = 500
            start = (page_num - 1) * page_size
            data = self.movie_repository.get_search_history(user_id, start, page_size)
            total = self.movie_repository.get_search_history_total(user_id)
            return ResultUtil.success(data=data, total=total)
        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(data=None, msg=f"获取搜索历史失败: {str(e)}")
