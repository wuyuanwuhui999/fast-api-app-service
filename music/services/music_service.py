from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from music.repositories.music_repository import MusicRepository
from music.schemas.music_favorite_schema import FavoriteDirectoryUpdateSchema
from music.schemas.music_query_schema import MusicQuerySchema
from music.schemas.music_record_schema import InsertMusicRecordSchema
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

    async def get_music_list_by_author_id(
            self,
            author_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        根据歌手ID分页查询音乐列表

        Args:
            author_id: 歌手ID
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 音乐列表（含点赞状态）
        """
        try:
            # 参数校验
            if author_id is None or author_id <= 0:
                return ResultUtil.fail(msg="歌手ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            # 查询音乐列表
            music_list, total = self.music_repository.get_music_list_by_author_id(
                author_id=author_id,
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取歌手音乐列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取歌手音乐列表失败: {str(e)}", data=None)

    async def get_favorite_authors(
            self,
            user_id: str
    ) -> ResultEntity:
        """
        获取当前用户喜欢的歌手列表

        根据用户ID查询歌手收藏表，再关联查询歌手详情

        Args:
            user_id: 当前用户ID

        Returns:
            ResultEntity: 歌手列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            # 查询用户喜欢的歌手列表
            author_list = self.music_repository.get_favorite_authors_by_user_id(
                user_id=user_id
            )

            # 使用 ResultUtil 返回数据
            return ResultUtil.success(data=author_list, total=len(author_list))

        except Exception as e:
            logger.error(f"获取用户喜欢的歌手列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取用户喜欢的歌手列表失败: {str(e)}", data=None)

    async def insert_favorite_author(
            self,
            user_id: str,
            author_id: int
    ) -> ResultEntity:
        """
        添加喜欢的歌手

        Args:
            user_id: 当前用户ID
            author_id: 歌手ID

        Returns:
            ResultEntity: 操作结果
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not author_id or author_id <= 0:
                return ResultUtil.fail(msg="歌手ID不能为空", data=None)

            # 检查歌手是否存在
            if not self.music_repository.check_author_exists(author_id):
                return ResultUtil.fail(msg=f"歌手不存在: author_id={author_id}", data=None)

            # 检查是否已喜欢
            if self.music_repository.check_favorite_exists(user_id, author_id):
                return ResultUtil.fail(msg="已喜欢该歌手，无需重复添加", data=None)

            # 添加喜欢的歌手
            success = self.music_repository.insert_favorite_author(user_id, author_id)

            if success:
                return ResultUtil.success(data=1, msg="添加喜欢歌手成功")
            else:
                return ResultUtil.fail(msg="添加喜欢歌手失败", data=None)

        except Exception as e:
            logger.error(f"添加喜欢的歌手失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"添加喜欢的歌手失败: {str(e)}", data=None)

    async def delete_favorite_author(
            self,
            user_id: str,
            author_id: int
    ) -> ResultEntity:
        """
        删除喜欢的歌手

        Args:
            user_id: 当前用户ID
            author_id: 歌手ID

        Returns:
            ResultEntity: 操作结果
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not author_id or author_id <= 0:
                return ResultUtil.fail(msg="歌手ID不能为空", data=None)

            # 检查是否已喜欢
            if not self.music_repository.check_favorite_exists(user_id, author_id):
                return ResultUtil.fail(msg="未喜欢该歌手，无需删除", data=None)

            # 删除喜欢的歌手
            success = self.music_repository.delete_favorite_author(user_id, author_id)

            if success:
                return ResultUtil.success(data=1, msg="取消喜欢歌手成功")
            else:
                return ResultUtil.fail(msg="取消喜欢歌手失败", data=None)

        except Exception as e:
            logger.error(f"删除喜欢的歌手失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"删除喜欢的歌手失败: {str(e)}", data=None)

    async def get_music_record(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page_num: int = 1,
        page_size: int = 20
    ) -> ResultEntity:
        """
        获取用户音乐播放记录

        按音乐去重，返回每首音乐的最新播放记录和播放总次数

        Args:
            user_id: 当前用户ID
            start_date: 开始时间（可选）
            end_date: 结束时间（可选）
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 播放记录列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 20
            if page_size > 500:
                page_size = 500

            # 验证时间范围
            if start_date and end_date and start_date > end_date:
                return ResultUtil.fail(msg="开始时间不能晚于结束时间", data=None)

            # 查询播放记录
            music_list, total = self.music_repository.get_music_record_with_times(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取音乐播放记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取音乐播放记录失败: {str(e)}", data=None)

    async def insert_music_record(
        self,
        user_id: str,
        record_data: InsertMusicRecordSchema
    ) -> ResultEntity:
        """
        添加音乐播放记录

        Args:
            user_id: 当前用户ID
            record_data: 播放记录请求数据

        Returns:
            ResultEntity: 新增记录ID
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not record_data.musicId or record_data.musicId <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 检查音乐是否存在
            if not self.music_repository.check_music_exists(record_data.musicId):
                return ResultUtil.fail(msg=f"音乐不存在: musicId={record_data.musicId}", data=None)

            # 插入播放记录
            result = self.music_repository.insert_music_record(
                music_id=record_data.musicId,
                user_id=user_id,
                platform=record_data.platform,
                version=record_data.version,
                device=record_data.device
            )

            if not result:
                return ResultUtil.fail(msg="插入播放记录失败", data=None)

            return ResultUtil.success(
                data=result.id,
                msg="播放记录添加成功"
            )

        except Exception as e:
            logger.error(f"添加音乐播放记录失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"添加播放记录失败: {str(e)}", data=None)

    async def insert_music_like(
        self,
        user_id: str,
        music_id: int
    ) -> ResultEntity:
        """
        添加音乐红心收藏

        Args:
            user_id: 当前用户ID
            music_id: 音乐ID

        Returns:
            ResultEntity: 新增记录ID
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not music_id or music_id <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 检查音乐是否存在
            if not self.music_repository.check_music_exists(music_id):
                return ResultUtil.fail(msg=f"音乐不存在: musicId={music_id}", data=None)

            # 添加收藏
            result = self.music_repository.insert_music_like(
                music_id=music_id,
                user_id=user_id
            )

            if result is None:
                return ResultUtil.fail(msg="添加收藏失败", data=None)

            if result == 0:
                return ResultUtil.fail(msg="您已收藏过该音乐", data=None)

            return ResultUtil.success(
                data=result,
                msg="收藏成功"
            )

        except Exception as e:
            logger.error(f"添加音乐收藏失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"添加收藏失败: {str(e)}", data=None)

    async def delete_music_like(
        self,
        user_id: str,
        music_id: int
    ) -> ResultEntity:
        """
        取消音乐红心收藏

        Args:
            user_id: 当前用户ID
            music_id: 音乐ID

        Returns:
            ResultEntity: 操作结果
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not music_id or music_id <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 检查是否已收藏
            if not self.music_repository.check_music_like_exists(music_id, user_id):
                return ResultUtil.fail(msg="您尚未收藏该音乐", data=None)

            # 取消收藏
            success = self.music_repository.delete_music_like(
                music_id=music_id,
                user_id=user_id
            )

            if not success:
                return ResultUtil.fail(msg="取消收藏失败", data=None)

            return ResultUtil.success(
                data=1,
                msg="取消收藏成功"
            )

        except Exception as e:
            logger.error(f"取消音乐收藏失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"取消收藏失败: {str(e)}", data=None)

    async def get_music_like_list(
        self,
        user_id: str,
        page_num: int = 1,
        page_size: int = 20
    ) -> ResultEntity:
        """
        获取用户收藏的音乐列表

        Args:
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 收藏音乐列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 20
            if page_size > 500:
                page_size = 500

            # 查询收藏音乐列表
            music_list, total = self.music_repository.get_music_like_list(
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取用户收藏音乐列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取收藏列表失败: {str(e)}", data=None)

    async def search_music(
        self,
        user_id: str,
        keyword: str,
        page_num: int = 1,
        page_size: int = 20
    ) -> ResultEntity:
        """
        根据关键词搜索音乐

        在 song_name、author_name、album_name 三个字段上执行模糊匹配
        返回结果包含当前用户的收藏状态

        Args:
            user_id: 当前用户ID
            keyword: 搜索关键词
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 搜索结果列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not keyword or not keyword.strip():
                return ResultUtil.fail(msg="搜索关键词不能为空", data=None)

            # 关键词长度限制（防止过长的搜索词）
            keyword = keyword.strip()
            if len(keyword) > 100:
                return ResultUtil.fail(msg="搜索关键词不能超过100个字符", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 20
            if page_size > 500:
                page_size = 500

            # 执行搜索
            music_list, total = self.music_repository.search_music_by_keyword(
                keyword=keyword,
                user_id=user_id,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"搜索音乐失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"搜索音乐失败: {str(e)}", data=None)

    async def query_music(
        self,
        user_id: str,
        query_params: MusicQuerySchema
    ) -> ResultEntity:
        """
        多条件查询音乐列表

        支持按歌曲名、歌手名、专辑名、语言、发布日期起始、标签进行组合查询
        所有条件均为可选

        Args:
            user_id: 当前用户ID
            query_params: 查询参数

        Returns:
            ResultEntity: 符合条件的音乐列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            # 构建查询参数
            song_name = query_params.songName
            author_name = query_params.authorName
            album_name = query_params.albumName
            language = query_params.language
            publish_start = query_params.publishStart
            label = query_params.label
            page_num = query_params.pageNum
            page_size = query_params.pageSize

            # 分页参数校验
            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 20
            if page_size > 500:
                page_size = 500

            # 执行查询
            music_list, total = self.music_repository.query_music_by_conditions(
                user_id=user_id,
                song_name=song_name,
                author_name=author_name,
                album_name=album_name,
                language=language,
                publish_start=publish_start,
                label=label,
                page_num=page_num,
                page_size=page_size
            )

            # 使用 ResultUtil 返回数据（自动转换驼峰）
            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"多条件查询音乐失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"查询音乐失败: {str(e)}", data=None)

    async def get_author_category_list(self) -> ResultEntity:
        """
        获取所有可用的歌手分类列表

        查询 disabled = 0 的分类，按 rank 降序排列

        Returns:
            ResultEntity: 歌手分类列表
        """
        try:
            category_list = self.music_repository.get_author_category_list()

            return ResultUtil.success(
                data=category_list,
                total=len(category_list)
            )

        except Exception as e:
            logger.error(f"获取歌手分类列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取歌手分类失败: {str(e)}", data=None)

    async def get_favorite_directory_list(
        self,
        user_id: str,
        music_id: int
    ) -> ResultEntity:
        """
        获取用户的所有音乐收藏夹列表

        Args:
            user_id: 当前用户ID
            music_id: 要检查的音乐ID

        Returns:
            ResultEntity: 收藏夹列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not music_id or music_id <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 获取收藏夹列表
            directory_list = self.music_repository.get_favorite_directory_list(
                user_id=user_id,
                music_id=music_id
            )

            return ResultUtil.success(
                data=directory_list,
                total=len(directory_list)
            )

        except Exception as e:
            logger.error(f"获取收藏夹列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取收藏夹列表失败: {str(e)}", data=None)

    async def create_favorite_directory(
        self,
        user_id: str,
        name: str
    ) -> ResultEntity:
        """
        创建音乐收藏夹

        Args:
            user_id: 当前用户ID
            name: 收藏夹名称

        Returns:
            ResultEntity: 创建的收藏夹
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not name or not name.strip():
                return ResultUtil.fail(msg="收藏夹名称不能为空", data=None)

            name = name.strip()
            if len(name) > 100:
                return ResultUtil.fail(msg="收藏夹名称不能超过100个字符", data=None)

            # 创建收藏夹
            result = self.music_repository.create_favorite_directory(
                user_id=user_id,
                name=name
            )

            if not result:
                return ResultUtil.fail(msg="收藏夹名称已存在", data=None)

            return ResultUtil.success(
                data=result,
                msg="收藏夹创建成功"
            )

        except Exception as e:
            logger.error(f"创建收藏夹失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"创建收藏夹失败: {str(e)}", data=None)

    async def delete_favorite_directory(
        self,
        user_id: str,
        directory_id: int
    ) -> ResultEntity:
        """
        删除音乐收藏夹

        Args:
            user_id: 当前用户ID
            directory_id: 收藏夹ID

        Returns:
            ResultEntity: 操作结果
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not directory_id or directory_id <= 0:
                return ResultUtil.fail(msg="收藏夹ID不能为空", data=None)

            # 删除收藏夹
            success = self.music_repository.delete_favorite_directory(
                user_id=user_id,
                directory_id=directory_id
            )

            if not success:
                return ResultUtil.fail(msg="收藏夹不存在或无权限删除", data=None)

            return ResultUtil.success(
                data=1,
                msg="收藏夹删除成功"
            )

        except Exception as e:
            logger.error(f"删除收藏夹失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"删除收藏夹失败: {str(e)}", data=None)

    async def get_music_list_by_favorite_id(
        self,
        user_id: str,
        favorite_id: int,
        page_num: int = 1,
        page_size: int = 20
    ) -> ResultEntity:
        """
        根据收藏夹ID获取音乐列表

        Args:
            user_id: 当前用户ID
            favorite_id: 收藏夹ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 音乐列表
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not favorite_id or favorite_id <= 0:
                return ResultUtil.fail(msg="收藏夹ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 20
            if page_size > 500:
                page_size = 500

            # 查询音乐列表
            music_list, total = self.music_repository.get_music_list_by_favorite_id(
                user_id=user_id,
                favorite_id=favorite_id,
                page_num=page_num,
                page_size=page_size
            )

            return ResultUtil.success(data=music_list, total=total)

        except Exception as e:
            logger.error(f"获取收藏夹音乐列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取音乐列表失败: {str(e)}", data=None)

    async def update_favorite_directory(
        self,
        user_id: str,
        update_data: FavoriteDirectoryUpdateSchema
    ) -> ResultEntity:
        """
        更新收藏夹名称

        Args:
            user_id: 当前用户ID
            update_data: 更新请求数据

        Returns:
            ResultEntity: 操作结果
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not update_data.id or update_data.id <= 0:
                return ResultUtil.fail(msg="收藏夹ID不能为空", data=None)

            if not update_data.name or not update_data.name.strip():
                return ResultUtil.fail(msg="收藏夹名称不能为空", data=None)

            name = update_data.name.strip()
            if len(name) > 100:
                return ResultUtil.fail(msg="收藏夹名称不能超过100个字符", data=None)

            # 更新收藏夹名称
            success = self.music_repository.update_favorite_directory(
                user_id=user_id,
                favorite_id=update_data.id,
                new_name=name
            )

            if not success:
                return ResultUtil.fail(msg="收藏夹不存在或无权限修改", data=None)

            return ResultUtil.success(data=1, msg="收藏夹名称更新成功")

        except Exception as e:
            logger.error(f"更新收藏夹名称失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"更新收藏夹名称失败: {str(e)}", data=None)

    async def is_music_favorite(
        self,
        user_id: str,
        music_id: int
    ) -> ResultEntity:
        """
        查询音乐是否已被当前用户收藏

        Args:
            user_id: 当前用户ID
            music_id: 音乐ID

        Returns:
            ResultEntity: 收藏数量
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not music_id or music_id <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 查询收藏数量
            count = self.music_repository.is_music_favorite(
                user_id=user_id,
                music_id=music_id
            )

            return ResultUtil.success(
                data=count,
                msg=None
            )

        except Exception as e:
            logger.error(f"查询音乐收藏状态失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"查询收藏状态失败: {str(e)}", data=None)

    async def insert_music_favorite(
        self,
        user_id: str,
        music_id: int,
        favorite_ids: List[int]
    ) -> ResultEntity:
        """
        将音乐添加到收藏夹

        先删除该音乐在所有收藏夹中的记录，再批量插入新的收藏记录

        Args:
            user_id: 当前用户ID
            music_id: 音乐ID
            favorite_ids: 收藏夹ID列表

        Returns:
            ResultEntity: 新增的收藏记录数
        """
        try:
            # 参数校验
            if not user_id:
                return ResultUtil.fail(msg="用户ID不能为空", data=None)

            if not music_id or music_id <= 0:
                return ResultUtil.fail(msg="音乐ID不能为空", data=None)

            # 如果收藏夹列表为空，相当于清空该音乐的所有收藏
            if favorite_ids is None:
                favorite_ids = []

            # 检查音乐是否存在
            if not self.music_repository.check_music_exists(music_id):
                return ResultUtil.fail(msg=f"音乐不存在: musicId={music_id}", data=None)

            # 添加音乐到收藏夹
            insert_count = self.music_repository.insert_music_favorite(
                user_id=user_id,
                music_id=music_id,
                favorite_ids=favorite_ids
            )

            if insert_count == 0 and favorite_ids:
                return ResultUtil.fail(msg="所有收藏夹均无效或无权限", data=None)

            return ResultUtil.success(
                data=insert_count,
                msg=f"已收藏到 {insert_count} 个收藏夹"
            )

        except Exception as e:
            logger.error(f"添加音乐到收藏夹失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"添加收藏失败: {str(e)}", data=None)

