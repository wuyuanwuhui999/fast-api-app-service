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

    async def get_recommend_music(
            self,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        获取推荐音乐列表（按 is_hot 降序）

        关联查询用户点赞状态（is_like: 1-已点赞，0-未点赞）

        Args:
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量（最大100）

        Returns:
            ResultEntity: 音乐列表（含分页信息）
        """
        try:
            # 参数校验
            if page_num < 1:
                page_num = 1
            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            # 查询数据
            music_list, total = self.music_repository.get_recommend_music_with_pagination(
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取推荐音乐列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取推荐音乐失败: {str(e)}", data=None)