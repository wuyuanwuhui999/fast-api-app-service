from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import func, and_, desc, select
from sqlalchemy.orm import Session, aliased
from fastapi.logger import logger

from music.models.music_model import MusicModel
from music.models.music_record import MusicRecordModel
from music.schemas.music_record_schema import MusicRecordResponseSchema


class MusicRepository:
    """音乐数据访问层"""

    def __init__(self, db: Session):
        self.db = db


    def get_keyword_music(
            self,
            user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取搜索框中推荐的一首音乐（按 is_hot 降序取第一条）
        使用 SQLAlchemy ORM 查询，返回包含用户点赞状态的字典

        Args:
            user_id: 当前用户ID

        Returns:
            Optional[Dict[str, Any]]: 音乐数据字典，如果未找到则返回 None
        """
        try:
            from music.models.music_model import MusicModel, MusicLikeModel
            from sqlalchemy import func

            # 使用 ORM 查询音乐（按 is_hot 降序，取第一条）
            # 使用 left join 查询点赞状态
            music = (
                self.db.query(
                    MusicModel,
                    func.if_(MusicLikeModel.id.isnot(None), 1, 0).label('is_like')
                )
                .outerjoin(
                    MusicLikeModel,
                    (MusicModel.id == MusicLikeModel.music_id) &
                    (MusicLikeModel.user_id == user_id)
                )
                .order_by(MusicModel.is_hot.desc())
                .first()
            )

            if not music:
                return None

            # 解包查询结果
            music_obj, is_like = music

            # 构建返回字典
            return {
                "id": music_obj.id,
                "album_id": music_obj.album_id,
                "song_name": music_obj.song_name,
                "author_name": music_obj.author_name,
                "author_id": music_obj.author_id,
                "album_name": music_obj.album_name,
                "version": music_obj.version,
                "language": music_obj.language,
                "publish_date": music_obj.publish_date,
                "wide_audio_id": music_obj.wide_audio_id,
                "is_publish": music_obj.is_publish,
                "big_pack_id": music_obj.big_pack_id,
                "final_id": music_obj.final_id,
                "audio_id": music_obj.audio_id,
                "similar_audio_id": music_obj.similar_audio_id,
                "is_hot": music_obj.is_hot,
                "album_audio_id": music_obj.album_audio_id,
                "audio_group_id": music_obj.audio_group_id,
                "cover": music_obj.cover,
                "play_url": music_obj.play_url,
                "local_play_url": music_obj.local_play_url,
                "source_name": music_obj.source_name,
                "source_url": music_obj.source_url,
                "create_time": music_obj.create_time,
                "update_time": music_obj.update_time,
                "label": music_obj.label,
                "lyrics": music_obj.lyrics,
                "is_like": is_like,  # 点赞状态：1-已点赞，0-未点赞
                "times": 0  # 播放次数，暂未实现
            }

        except Exception as e:
            logger.error(f"获取推荐音乐失败: {str(e)}", exc_info=True)
            return None

    def get_music_classify_list(self) -> List[Dict[str, Any]]:
        """
        获取音乐分类列表
        按 classify_rank 降序排列

        Returns:
            List[Dict[str, Any]]: 分类列表
        """
        try:
            from music.models.music_classify_relation import MusicClassifyRelationModel

            results = (
                self.db.query(MusicClassifyRelationModel)
                .filter(
                    MusicClassifyRelationModel.disabled == 0,
                    MusicClassifyRelationModel.permission >= 0
                )
                .order_by(MusicClassifyRelationModel.classify_rank.desc())
                .all()
            )

            return [
                {
                    "id": item.id,
                    "classify_name": item.classify_name,
                    "permission": item.permission,
                    "classify_rank": item.classify_rank,
                    "cover": item.cover,
                    "disabled": item.disabled,
                    "create_time": item.create_time,
                    "update_time": item.update_time
                }
                for item in results
            ]

        except Exception as e:
            logger.error(f"获取音乐分类列表失败: {str(e)}", exc_info=True)
            return []

    def get_music_list_by_classify_id(
            self,
            classify_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        根据分类ID分页查询音乐列表，并获取当前用户的点赞状态

        Args:
            classify_id: 分类ID
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[Dict[str, Any]], int]: (音乐列表, 总记录数)
        """
        try:
            from music.models.music_classify import MusicClassifyModel
            from music.models.music_model import MusicModel, MusicLikeModel
            from sqlalchemy import func, desc

            offset = (page_num - 1) * page_size

            # ==================== 查询总数 ====================
            total_stmt = (
                self.db.query(func.count(MusicClassifyModel.id))
                .filter(MusicClassifyModel.classify_id == classify_id)
            )
            total = total_stmt.scalar() or 0

            if total == 0:
                return [], 0

            # ==================== 查询音乐列表 ====================
            # 主查询：通过 music_classify 关联 music 表，并 LEFT JOIN 点赞表
            results = (
                self.db.query(
                    MusicModel,
                    MusicClassifyModel.audio_rank,
                    func.if_(MusicLikeModel.id.isnot(None), 1, 0).label('is_like')
                )
                .join(
                    MusicClassifyModel,
                    MusicModel.id == MusicClassifyModel.music_id
                )
                .outerjoin(
                    MusicLikeModel,
                    (MusicModel.id == MusicLikeModel.music_id) &
                    (MusicLikeModel.user_id == user_id)
                )
                .filter(MusicClassifyModel.classify_id == classify_id)
                .order_by(
                    MusicClassifyModel.audio_rank.desc(),
                    MusicModel.create_time.desc()
                )
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # 构建返回数据
            music_list = []
            for music_obj, audio_rank, is_like in results:
                music_dict = {
                    "id": music_obj.id,
                    "album_id": music_obj.album_id,
                    "song_name": music_obj.song_name,
                    "author_name": music_obj.author_name,
                    "author_id": music_obj.author_id,
                    "album_name": music_obj.album_name,
                    "version": music_obj.version,
                    "language": music_obj.language,
                    "publish_date": music_obj.publish_date,
                    "wide_audio_id": music_obj.wide_audio_id,
                    "is_publish": music_obj.is_publish,
                    "big_pack_id": music_obj.big_pack_id,
                    "final_id": music_obj.final_id,
                    "audio_id": music_obj.audio_id,
                    "similar_audio_id": music_obj.similar_audio_id,
                    "is_hot": music_obj.is_hot,
                    "album_audio_id": music_obj.album_audio_id,
                    "audio_group_id": music_obj.audio_group_id,
                    "cover": music_obj.cover,
                    "play_url": music_obj.play_url,
                    "local_play_url": music_obj.local_play_url,
                    "source_name": music_obj.source_name,
                    "source_url": music_obj.source_url,
                    "create_time": music_obj.create_time,
                    "update_time": music_obj.update_time,
                    "label": music_obj.label,
                    "lyrics": music_obj.lyrics,
                    "permission": music_obj.permission,
                    "audio_rank": audio_rank,
                    "is_like": is_like,  # 点赞状态：1-已点赞，0-未点赞
                    "times": 0  # 播放次数，暂未实现
                }
                music_list.append(music_dict)

            return music_list, total

        except Exception as e:
            logger.error(f"根据分类ID查询音乐列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_author_list_by_category_id(
            self,
            category_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        根据分类ID分页查询歌手列表，并获取每个歌手的歌曲数量和当前用户的点赞状态

        Args:
            category_id: 分类ID
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[Dict[str, Any]], int]: (歌手列表, 总记录数)
        """
        try:
            from music.models.music_author import MusicAuthorModel
            from music.models.music_author_like import MusicAuthorLikeModel
            from music.models.music_model import MusicModel
            from sqlalchemy import func, desc

            offset = (page_num - 1) * page_size

            # ==================== 查询总数 ====================
            total_stmt = (
                self.db.query(func.count(MusicAuthorModel.id))
                .filter(
                    MusicAuthorModel.category_id == category_id,
                    MusicAuthorModel.is_publish == 1
                )
            )
            total = total_stmt.scalar() or 0

            if total == 0:
                return [], 0

            # ==================== 子查询：统计每个歌手的歌曲数量 ====================
            # 按 author_id 分组统计 music 表中的歌曲数量
            music_count_subquery = (
                self.db.query(
                    MusicModel.author_id,
                    func.count(MusicModel.id).label('song_count')
                )
                .filter(MusicModel.is_publish == 1)
                .group_by(MusicModel.author_id)
                .subquery()
            )

            # ==================== 主查询：歌手列表 + 歌曲数量 + 点赞状态 ====================
            results = (
                self.db.query(
                    MusicAuthorModel,
                    func.coalesce(music_count_subquery.c.song_count, 0).label('total'),
                    func.if_(MusicAuthorLikeModel.id.isnot(None), 1, 0).label('is_like')
                )
                .outerjoin(
                    music_count_subquery,
                    MusicAuthorModel.author_id == music_count_subquery.c.author_id
                )
                .outerjoin(
                    MusicAuthorLikeModel,
                    (MusicAuthorModel.id == MusicAuthorLikeModel.author_id) &
                    (MusicAuthorLikeModel.user_id == user_id)
                )
                .filter(
                    MusicAuthorModel.category_id == category_id,
                    MusicAuthorModel.is_publish == 1
                )
                .order_by(
                    func.coalesce(MusicAuthorModel.rank, 0).desc(),
                    MusicAuthorModel.author_name.asc()
                )
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # 构建返回数据
            author_list = []
            for author_obj, total_songs, is_like in results:
                author_dict = {
                    "id": author_obj.id,
                    "author_id": author_obj.author_id,
                    "author_name": author_obj.author_name,
                    "category_id": author_obj.category_id,
                    "is_publish": author_obj.is_publish,
                    "avatar": author_obj.avatar,
                    "type": author_obj.type,
                    "country": author_obj.country,
                    "birthday": author_obj.birthday,
                    "identity": author_obj.identity,
                    "rank": author_obj.rank,
                    "create_time": author_obj.create_time,
                    "update_time": author_obj.update_time,
                    "total": total_songs,  # 歌曲数量
                    "is_like": is_like  # 点赞状态：1-已点赞，0-未点赞
                }
                author_list.append(author_dict)

            return author_list, total

        except Exception as e:
            logger.error(f"根据分类ID查询歌手列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_music_list_by_author_id(
            self,
            author_id: int,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        根据歌手ID分页查询音乐列表，并获取当前用户的点赞状态

        Args:
            author_id: 歌手ID（对应 music 表的 author_id 字段）
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[Dict[str, Any]], int]: (音乐列表, 总记录数)
        """
        try:
            from music.models.music_model import MusicModel, MusicLikeModel
            from sqlalchemy import func, desc

            offset = (page_num - 1) * page_size

            # ==================== 查询总数 ====================
            total_stmt = (
                self.db.query(func.count(MusicModel.id))
                .filter(
                    MusicModel.author_id == author_id,
                    MusicModel.is_publish == 1
                )
            )
            total = total_stmt.scalar() or 0

            if total == 0:
                return [], 0

            # ==================== 查询音乐列表 ====================
            # 主查询：查询音乐列表，并 LEFT JOIN 点赞表
            results = (
                self.db.query(
                    MusicModel,
                    func.if_(MusicLikeModel.id.isnot(None), 1, 0).label('is_like')
                )
                .outerjoin(
                    MusicLikeModel,
                    (MusicModel.id == MusicLikeModel.music_id) &
                    (MusicLikeModel.user_id == user_id)
                )
                .filter(
                    MusicModel.author_id == author_id,
                    MusicModel.is_publish == 1
                )
                .order_by(
                    func.coalesce(MusicModel.is_hot, 0).desc(),
                    MusicModel.create_time.desc()
                )
                .offset(offset)
                .limit(page_size)
                .all()
            )

            # 构建返回数据
            music_list = []
            for music_obj, is_like in results:
                music_dict = {
                    "id": music_obj.id,
                    "album_id": music_obj.album_id,
                    "song_name": music_obj.song_name,
                    "author_name": music_obj.author_name,
                    "author_id": music_obj.author_id,
                    "album_name": music_obj.album_name,
                    "version": music_obj.version,
                    "language": music_obj.language,
                    "publish_date": music_obj.publish_date,
                    "wide_audio_id": music_obj.wide_audio_id,
                    "is_publish": music_obj.is_publish,
                    "big_pack_id": music_obj.big_pack_id,
                    "final_id": music_obj.final_id,
                    "audio_id": music_obj.audio_id,
                    "similar_audio_id": music_obj.similar_audio_id,
                    "is_hot": music_obj.is_hot,
                    "album_audio_id": music_obj.album_audio_id,
                    "audio_group_id": music_obj.audio_group_id,
                    "cover": music_obj.cover,
                    "play_url": music_obj.play_url,
                    "local_play_url": music_obj.local_play_url,
                    "source_name": music_obj.source_name,
                    "source_url": music_obj.source_url,
                    "create_time": music_obj.create_time,
                    "update_time": music_obj.update_time,
                    "label": music_obj.label,
                    "lyrics": music_obj.lyrics,
                    "permission": music_obj.permission,
                    "is_like": is_like,  # 点赞状态：1-已点赞，0-未点赞
                    "times": 0  # 播放次数，暂未实现
                }
                music_list.append(music_dict)

            return music_list, total

        except Exception as e:
            logger.error(f"根据歌手ID查询音乐列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_favorite_authors_by_user_id(
            self,
            user_id: str
    ) -> List[Dict[str, Any]]:
        """
        根据用户ID获取用户喜欢的歌手列表

        查询逻辑：
        1. 从 music_author_like 表查询用户收藏的歌手ID列表
        2. 根据 author_id 关联查询 music_authors 表获取歌手详情

        Args:
            user_id: 当前用户ID

        Returns:
            List[Dict[str, Any]]: 歌手列表（包含歌手详情）
        """
        try:
            from music.models.music_author import MusicAuthorModel
            from music.models.music_author_like import MusicAuthorLikeModel
            from sqlalchemy import desc

            # 使用 INNER JOIN 查询用户收藏的歌手
            results = (
                self.db.query(MusicAuthorModel)
                .join(
                    MusicAuthorLikeModel,
                    MusicAuthorModel.author_id == MusicAuthorLikeModel.author_id
                )
                .filter(
                    MusicAuthorLikeModel.user_id == user_id,
                    MusicAuthorModel.is_publish == 1
                )
                .order_by(
                    MusicAuthorLikeModel.create_time.desc()
                )
                .all()
            )

            # 构建返回数据
            author_list = []
            for author_obj in results:
                author_dict = {
                    "id": author_obj.id,
                    "author_id": author_obj.author_id,
                    "author_name": author_obj.author_name,
                    "category_id": author_obj.category_id,
                    "is_publish": author_obj.is_publish,
                    "avatar": author_obj.avatar,
                    "type": author_obj.type,
                    "country": author_obj.country,
                    "birthday": author_obj.birthday,
                    "identity": author_obj.identity,
                    "rank": author_obj.rank,
                    "create_time": author_obj.create_time,
                    "update_time": author_obj.update_time
                }
                author_list.append(author_dict)

            return author_list

        except Exception as e:
            logger.error(f"获取用户喜欢的歌手列表失败: {str(e)}", exc_info=True)
            return []

    def insert_favorite_author(
            self,
            user_id: str,
            author_id: int
    ) -> bool:
        """
        添加喜欢的歌手

        检查是否已存在，如果不存在则插入新记录

        Args:
            user_id: 当前用户ID
            author_id: 歌手ID（关联 music_authors 表的 author_id 字段）

        Returns:
            bool: 是否添加成功（True=成功，False=失败或已存在）
        """
        try:
            from music.models.music_author_like import MusicAuthorLikeModel
            from datetime import datetime

            # 检查是否已存在
            existing = self.db.query(MusicAuthorLikeModel).filter(
                MusicAuthorLikeModel.user_id == user_id,
                MusicAuthorLikeModel.author_id == author_id
            ).first()

            if existing:
                logger.info(f"用户 {user_id} 已喜欢歌手 {author_id}，无需重复添加")
                return False

            # 检查歌手是否存在
            from music.models.music_author import MusicAuthorModel
            author = self.db.query(MusicAuthorModel).filter(
                MusicAuthorModel.author_id == author_id,
                MusicAuthorModel.is_publish == 1
            ).first()

            if not author:
                logger.warning(f"歌手不存在: author_id={author_id}")
                return False

            # 插入新记录
            new_like = MusicAuthorLikeModel(
                author_id=author_id,
                user_id=user_id,
                create_time=datetime.now()
            )

            self.db.add(new_like)
            self.db.commit()

            logger.info(f"用户 {user_id} 添加喜欢的歌手成功: author_id={author_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"添加喜欢的歌手失败: {str(e)}", exc_info=True)
            return False

    def delete_favorite_author(
            self,
            user_id: str,
            author_id: int
    ) -> bool:
        """
        删除喜欢的歌手

        Args:
            user_id: 当前用户ID
            author_id: 歌手ID（关联 music_authors 表的 author_id 字段）

        Returns:
            bool: 是否删除成功（True=成功，False=失败或不存在）
        """
        try:
            from music.models.music_author_like import MusicAuthorLikeModel

            # 查询记录
            existing = self.db.query(MusicAuthorLikeModel).filter(
                MusicAuthorLikeModel.user_id == user_id,
                MusicAuthorLikeModel.author_id == author_id
            ).first()

            if not existing:
                logger.info(f"用户 {user_id} 未喜欢歌手 {author_id}，无需删除")
                return False

            # 删除记录
            self.db.delete(existing)
            self.db.commit()

            logger.info(f"用户 {user_id} 删除喜欢的歌手成功: author_id={author_id}")
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除喜欢的歌手失败: {str(e)}", exc_info=True)
            return False

    def check_author_exists(self, author_id: int) -> bool:
        """
        检查歌手是否存在且已发布

        Args:
            author_id: 歌手ID

        Returns:
            bool: 是否存在
        """
        try:
            from music.models.music_author import MusicAuthorModel

            author = self.db.query(MusicAuthorModel).filter(
                MusicAuthorModel.author_id == author_id,
                MusicAuthorModel.is_publish == 1
            ).first()

            return author is not None

        except Exception as e:
            logger.error(f"检查歌手是否存在失败: {str(e)}", exc_info=True)
            return False

    def check_favorite_exists(self, user_id: str, author_id: int) -> bool:
        """
        检查用户是否已喜欢该歌手

        Args:
            user_id: 用户ID
            author_id: 歌手ID

        Returns:
            bool: 是否已喜欢
        """
        try:
            from music.models.music_author_like import MusicAuthorLikeModel

            existing = self.db.query(MusicAuthorLikeModel).filter(
                MusicAuthorLikeModel.user_id == user_id,
                MusicAuthorLikeModel.author_id == author_id
            ).first()

            return existing is not None

        except Exception as e:
            logger.error(f"检查喜欢状态失败: {str(e)}", exc_info=True)
            return False

    def get_music_record_with_times(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page_num: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取用户播放记录，按音乐去重，返回最新播放记录和播放总次数

        使用 SQLAlchemy ORM 实现：
        1. 子查询1: 按 user_id 和 (可选) 时间范围过滤播放记录
        2. 子查询2: 按 music_id 分组，取 MAX(create_time) 作为最新播放时间
        3. 关联音乐表获取音乐详情
        4. 关联统计子查询获取每首音乐的播放总次数

        Args:
            user_id: 用户ID
            start_date: 开始时间（可选）
            end_date: 结束时间（可选）
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[Dict[str, Any]], int]: (音乐列表, 总记录数)
        """
        try:
            # ============================================================
            # 第1步：构建基础查询（过滤用户和时间范围）
            # ============================================================
            base_query = self.db.query(MusicRecordModel).filter(
                MusicRecordModel.user_id == user_id
            )

            if start_date:
                base_query = base_query.filter(MusicRecordModel.create_time >= start_date)
            if end_date:
                base_query = base_query.filter(MusicRecordModel.create_time <= end_date)

            # ============================================================
            # 第2步：子查询 - 获取每首音乐的最新播放时间
            # ============================================================
            # 使用 subquery 构建：SELECT music_id, MAX(create_time) AS max_date
            # FROM music_record WHERE user_id = :user_id ... GROUP BY music_id
            latest_subq = (
                base_query
                .with_entities(
                    MusicRecordModel.music_id,
                    func.max(MusicRecordModel.create_time).label("max_date")
                )
                .group_by(MusicRecordModel.music_id)
                .subquery("latest")
            )

            # ============================================================
            # 第3步：子查询 - 获取最新播放记录的完整信息
            # ============================================================
            # 将 base_query 作为子查询，内连接 latest_subq 获取最新记录
            # 使用 aliased 来引用 MusicRecordModel 作为不同的表别名
            RecordAlias = aliased(MusicRecordModel)

            # 构建最新记录的子查询
            # SELECT RecordAlias.*
            # FROM music_record AS RecordAlias
            # INNER JOIN latest ON RecordAlias.music_id = latest.music_id
            #   AND RecordAlias.create_time = latest.max_date
            # ORDER BY RecordAlias.create_time DESC
            latest_records_subq = (
                self.db.query(RecordAlias)
                .join(
                    latest_subq,
                    and_(
                        RecordAlias.music_id == latest_subq.c.music_id,
                        RecordAlias.create_time == latest_subq.c.max_date
                    )
                )
                .order_by(desc(RecordAlias.create_time))
                .subquery("latest_records")
            )

            # ============================================================
            # 第4步：子查询 - 统计每首音乐的播放总次数
            # ============================================================
            # SELECT COUNT(music_id) AS times, music_id
            # FROM music_record WHERE user_id = :user_id ...
            # GROUP BY music_id
            count_subq = (
                base_query
                .with_entities(
                    MusicRecordModel.music_id,
                    func.count(MusicRecordModel.music_id).label("times")
                )
                .group_by(MusicRecordModel.music_id)
                .subquery("counts")
            )

            # ============================================================
            # 第5步：主查询 - 关联音乐表和统计表
            # ============================================================
            # SELECT music.*, counts.times
            # FROM latest_records AS lr
            # INNER JOIN music ON lr.music_id = music.id
            # INNER JOIN counts ON lr.music_id = counts.music_id
            # ORDER BY lr.create_time DESC
            # LIMIT ... OFFSET ...
            stmt = (
                select(
                    MusicModel,
                    func.coalesce(count_subq.c.times, 0).label("times")
                )
                .select_from(latest_records_subq)
                .join(MusicModel, latest_records_subq.c.music_id == MusicModel.id)
                .join(count_subq, latest_records_subq.c.music_id == count_subq.c.music_id)
                .order_by(desc(latest_records_subq.c.create_time))
            )

            # ============================================================
            # 第6步：查询总数
            # ============================================================
            total_stmt = select(func.count()).select_from(latest_records_subq)
            total = self.db.execute(total_stmt).scalar() or 0

            # ============================================================
            # 第7步：分页查询
            # ============================================================
            offset = (page_num - 1) * page_size
            stmt = stmt.offset(offset).limit(page_size)

            results = self.db.execute(stmt).all()

            # ============================================================
            # 第8步：构建返回数据
            # ============================================================
            music_list = []
            for music_obj, times in results:
                # 使用已有的音乐模型转字典方法
                music_dict = self._music_to_dict(music_obj)
                music_dict["times"] = int(times) if times else 0
                music_list.append(music_dict)

            return music_list, total

        except Exception as e:
            logger.error(f"获取音乐播放记录失败: {str(e)}", exc_info=True)
            return [], 0

    def _music_to_dict(self, music_obj) -> Dict[str, Any]:
        """将 MusicModel 对象转换为字典（保留原始字段名，后续由 ResultUtil 转换驼峰）"""
        return {
            "id": music_obj.id,
            "album_id": music_obj.album_id,
            "song_name": music_obj.song_name,
            "author_name": music_obj.author_name,
            "author_id": music_obj.author_id,
            "album_name": music_obj.album_name,
            "version": music_obj.version,
            "language": music_obj.language,
            "publish_date": music_obj.publish_date,
            "wide_audio_id": music_obj.wide_audio_id,
            "is_publish": music_obj.is_publish,
            "big_pack_id": music_obj.big_pack_id,
            "final_id": music_obj.final_id,
            "audio_id": music_obj.audio_id,
            "similar_audio_id": music_obj.similar_audio_id,
            "is_hot": music_obj.is_hot,
            "album_audio_id": music_obj.album_audio_id,
            "audio_group_id": music_obj.audio_group_id,
            "cover": music_obj.cover,
            "play_url": music_obj.play_url,
            "local_play_url": music_obj.local_play_url,
            "source_name": music_obj.source_name,
            "source_url": music_obj.source_url,
            "create_time": music_obj.create_time,
            "update_time": music_obj.update_time,
            "label": music_obj.label,
            "lyrics": music_obj.lyrics,
            "permission": music_obj.permission,
        }
    def insert_music_record(
        self,
        music_id: int,
        user_id: str,
        platform: Optional[str] = None,
        version: Optional[str] = None,
        device: Optional[str] = None
    ) -> Optional[MusicRecordResponseSchema]:
        """
        插入音乐播放记录

        Args:
            music_id: 音乐ID
            user_id: 用户ID
            platform: 播放平台（可选）
            version: App版本号（可选）
            device: 设备型号（可选）

        Returns:
            Optional[MusicRecordResponseSchema]: 创建的记录，失败返回None
        """
        try:
            from music.models.music_record import MusicRecordModel

            db_record = MusicRecordModel(
                music_id=music_id,
                user_id=user_id,
                platform=platform,
                version=version,
                device=device
            )

            self.db.add(db_record)
            self.db.commit()
            self.db.refresh(db_record)

            return MusicRecordResponseSchema.model_validate(db_record)

        except Exception as e:
            self.db.rollback()
            logger.error(f"插入音乐播放记录失败: {str(e)}", exc_info=True)
            return None

    def check_music_exists(self, music_id: int) -> bool:
        """检查音乐是否存在"""
        try:
            from music.models.music_model import MusicModel

            music = self.db.query(MusicModel).filter(
                MusicModel.id == music_id,
                MusicModel.is_publish == 1
            ).first()

            return music is not None

        except Exception as e:
            logger.error(f"检查音乐是否存在失败: {str(e)}", exc_info=True)
            return False

