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

    def get_recommend_music_with_pagination(
            self,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取推荐音乐列表（按 is_hot 降序），关联查询用户点赞状态

        使用原生 SQL 查询，支持分页

        Args:
            user_id: 当前用户ID
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[Dict], int]: (音乐列表, 总记录数)
        """
        try:
            offset = (page_num - 1) * page_size

            # ==================== 查询总数 ====================
            count_sql = "SELECT COUNT(*) FROM music"
            total_result = self.db.execute(text(count_sql))
            total = total_result.scalar() or 0

            if total == 0:
                return [], 0

            # ==================== 查询数据列表 ====================
            # 主查询：按 is_hot 降序，关联 music_like 表查询点赞状态
            data_sql = """
                       SELECT m.id, \
                              m.album_id, \
                              m.song_name, \
                              m.author_name, \
                              m.author_id, \
                              m.album_name, \
                              m.version, \
                              m.language, \
                              m.publish_date, \
                              m.wide_audio_id, \
                              m.is_publish, \
                              m.big_pack_id, \
                              m.final_id, \
                              m.audio_id, \
                              m.similar_audio_id, \
                              m.is_hot, \
                              m.album_audio_id, \
                              m.audio_group_id, \
                              m.cover, \
                              m.play_url, \
                              m.local_play_url, \
                              m.source_name, \
                              m.source_url, \
                              m.create_time, \
                              m.update_time, \
                              m.label, \
                              m.lyrics, \
                              CASE WHEN ml.id IS NOT NULL THEN 1 ELSE 0 END AS is_like
                       FROM music m
                                LEFT JOIN music_like ml
                                          ON m.id = ml.music_id
                                              AND ml.user_id = :user_id
                       ORDER BY m.is_hot DESC LIMIT :limit \
                       OFFSET :offset \
                       """

            result = self.db.execute(
                text(data_sql),
                {
                    "user_id": user_id,
                    "limit": page_size,
                    "offset": offset
                }
            )

            rows = result.fetchall()
            music_list = []

            for row in rows:
                music_dict = {
                    "id": row[0],
                    "album_id": row[1],
                    "song_name": row[2],
                    "author_name": row[3],
                    "author_id": row[4],
                    "album_name": row[5],
                    "version": row[6],
                    "language": row[7],
                    "publish_date": row[8],
                    "wide_audio_id": row[9],
                    "is_publish": row[10],
                    "big_pack_id": row[11],
                    "final_id": row[12],
                    "audio_id": row[13],
                    "similar_audio_id": row[14],
                    "is_hot": row[15],
                    "album_audio_id": row[16],
                    "audio_group_id": row[17],
                    "cover": row[18],
                    "play_url": row[19],
                    "local_play_url": row[20],
                    "source_name": row[21],
                    "source_url": row[22],
                    "create_time": row[23],
                    "update_time": row[24],
                    "label": row[25],
                    "lyrics": row[26],
                    "is_like": row[27],  # 从 LEFT JOIN 计算得出
                    "times": 0  # 播放次数，暂未实现
                }
                music_list.append(music_dict)

            return music_list, total

        except Exception as e:
            logger.error(f"获取推荐音乐列表失败: {str(e)}", exc_info=True)
            return [], 0