# music/services/music_service.py
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from music.repositories.music_repository import MusicRepository
from music.schemas.music_schema import MusicQueryParams


class MusicService:
    """音乐服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.music_repository = MusicRepository(db)

    async def get_keyword_music(
            self,
            user_id: str
    ) -> ResultEntity:
        """
        获取搜索框中推荐的一首音乐（按 is_hot 降序取第一条）

        Args:
            user_id: 当前用户ID

        Returns:
            ResultEntity: 单首音乐数据（含点赞状态）
        """
        try:
            # 查询推荐音乐
            music_data = self.music_repository.get_keyword_music(
                user_id=user_id
            )

            if not music_data:
                return ResultUtil.fail(msg="暂无推荐音乐", data=None)

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_data)

        except Exception as e:
            logger.error(f"获取推荐音乐失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取推荐音乐失败: {str(e)}", data=None)

    async def get_music_classify(self) -> ResultEntity:
        """
        获取音乐分类列表
        按 classify_rank 降序排列

        Returns:
            ResultEntity: 分类列表
        """
        try:
            classify_list = self.music_repository.get_music_classify_list()

            if not classify_list:
                return ResultUtil.success(data=[], total=0, msg="暂无分类数据")

            return ResultUtil.success(data=classify_list, total=len(classify_list))

        except Exception as e:
            logger.error(f"获取音乐分类失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取音乐分类失败: {str(e)}", data=None)

    async def get_music_list_by_classify_id(
            self,
            classify_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        根据分类ID分页查询音乐列表

        Args:
            classify_id: 分类ID
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 音乐列表（含点赞状态）
        """
        try:
            # 参数校验
            if classify_id is None or classify_id <= 0:
                return ResultUtil.fail(msg="分类ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            # 查询音乐列表
            music_list, total = self.music_repository.get_music_list_by_classify_id(
                classify_id=classify_id,
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取分类音乐列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取分类音乐列表失败: {str(e)}", data=None)

    async def get_author_list_by_category_id(
            self,
            category_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        根据分类ID分页查询歌手列表

        Args:
            category_id: 分类ID
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 歌手列表（含歌曲数量和点赞状态）
        """
        try:
            # 参数校验
            if category_id is None or category_id <= 0:
                return ResultUtil.fail(msg="分类ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            # 查询歌手列表
            author_list, total = self.music_repository.get_author_list_by_category_id(
                category_id=category_id,
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=author_list, total=total)

        except Exception as e:
            logger.error(f"获取分类歌手列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取分类歌手列表失败: {str(e)}", data=None)