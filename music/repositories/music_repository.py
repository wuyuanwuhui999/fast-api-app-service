# music/repositories/music_repository.py
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, desc
from fastapi.logger import logger

from music.models.music_model import MusicModel, MusicLikeModel
from music.schemas.music_schema import MusicSchema


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