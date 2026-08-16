# circle/repositories/circle_repository.py
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session
from fastapi.logger import logger

from circle.models.circle_model import Circle


class CircleRepository:
    """朋友圈数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 查询 ====================

    def get_circle_count(self, circle_type: str) -> int:
        """获取指定类型的朋友圈总数"""
        try:
            sql = "SELECT COUNT(id) FROM circle WHERE `type` = :type"
            result = self.db.execute(text(sql), {"type": circle_type}).scalar()
            return result or 0
        except Exception as e:
            logger.error(f"获取朋友圈总数失败: {str(e)}", exc_info=True)
            return 0

    def get_circle_list_by_type(
            self,
            start: int,
            page_size: int,
            circle_type: str
    ) -> List[Dict[str, Any]]:
        """
        分页获取朋友圈列表（含点赞、评论嵌套）

        对应 Spring 中 getCircleListByType 的 MyBatis 动态 SQL：
        - type == MUSIC 时 LEFT JOIN music 表
        - type == MOVIE 时 LEFT JOIN movie 表
        - 始终 LEFT JOIN user 表
        """
        try:
            music_columns = ""
            movie_columns = ""
            join_sql = ""

            if circle_type == "MUSIC":
                music_columns = """
                    m.song_name AS music_song_name,
                    m.audio_id AS music_audio_id,
                    m.author_name AS music_author_name,
                    m.album_name AS music_album_name,
                    m.cover AS music_cover,
                    CASE WHEN 0 >= m.permission THEN m.play_url ELSE NULL END AS music_play_url,
                    CASE WHEN 0 >= m.permission THEN m.local_play_url ELSE NULL END AS music_local_play_url,
                    CASE WHEN 0 >= m.permission THEN m.lyrics ELSE NULL END AS music_lyrics,
                """
                join_sql = "LEFT JOIN music m ON c.relation_id = m.id"
            elif circle_type == "MOVIE":
                movie_columns = """
                    o.ext_movie_id AS movie_id,
                    o.movie_name AS movie_name,
                    o.director AS movie_director,
                    o.star AS movie_star,
                    o.type AS movie_type,
                    o.country_language AS movie_country_language,
                    o.viewing_state AS movie_viewing_state,
                    o.release_time AS movie_release_time,
                    o.img AS movie_img,
                    o.classify AS movie_classify,
                    o.local_img AS movie_local_img,
                    o.score AS movie_score,
                """
                join_sql = "LEFT JOIN movie o ON c.relation_id = o.id"

            sql = f"""
                SELECT
                    c.id,
                    c.relation_id,
                    c.content,
                    c.imgs,
                    c.type,
                    c.user_id,
                    c.permission,
                    c.create_time,
                    c.update_time,
                    {music_columns}
                    {movie_columns}
                    u.username,
                    u.avater AS useravater
                FROM circle c
                LEFT JOIN user u ON c.user_id COLLATE utf8mb4_unicode_ci = u.id
                {join_sql}
                WHERE c.type = :type AND c.permission = 1
                ORDER BY c.create_time DESC
                LIMIT :start, :page_size
            """

            rows = self.db.execute(
                text(sql),
                {"type": circle_type, "start": start, "page_size": page_size}
            ).mappings().all()

            circle_list = []
            for row in rows:
                item = self._row_to_dict(row)
                item["circle_likes"] = self.get_circle_like_by_circle_id(item["id"])
                item["circle_comments"] = self.get_social_comment_by_circle_id(item["id"])
                circle_list.append(item)

            return circle_list
        except Exception as e:
            logger.error(f"获取朋友圈列表失败: {str(e)}", exc_info=True)
            return []

    def get_circle_like_by_circle_id(self, circle_id: int) -> List[Dict[str, Any]]:
        """获取朋友圈点赞列表（type=MUSIC_CIRCLE）"""
        try:
            sql = """
                SELECT
                    c.id,
                    c.type,
                    c.user_id,
                    c.relation_id,
                    c.create_time,
                    c.update_time,
                    u.username
                FROM social_like c
                LEFT JOIN user u ON CONVERT(c.user_id USING utf8mb4) COLLATE utf8mb4_unicode_ci = u.id
                WHERE c.relation_id = :circle_id AND c.type = 'MUSIC_CIRCLE'
            """
            rows = self.db.execute(text(sql), {"circle_id": circle_id}).mappings().all()
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取朋友圈点赞列表失败: {str(e)}", exc_info=True)
            return []

    def get_social_comment_by_circle_id(self, circle_id: int) -> List[Dict[str, Any]]:
        """获取朋友圈一级评论列表（含回复数、被回复人），并嵌套前5条回复"""
        try:
            sql = """
                SELECT
                    t6.id,
                    t6.content,
                    t6.parent_id,
                    t6.top_id,
                    t6.relation_id,
                    t6.type,
                    t6.user_id,
                    t6.create_time,
                    t6.update_time,
                    t6.username,
                    t6.avater,
                    t6.reply_user_id,
                    t6.reply_user_name,
                    COALESCE(t7.cnt, 0) AS reply_count
                FROM (
                    SELECT
                        t4.id,
                        t4.content,
                        t4.parent_id,
                        t4.top_id,
                        t4.relation_id,
                        t4.type,
                        t4.user_id,
                        t4.create_time,
                        t4.update_time,
                        t4.username,
                        t4.avater,
                        t4.reply_user_id,
                        t5.username AS reply_user_name
                    FROM (
                        SELECT
                            t1.id,
                            t1.content,
                            t1.parent_id,
                            t1.top_id,
                            t1.relation_id,
                            t1.type,
                            t1.user_id,
                            t1.create_time,
                            t1.udate_time AS update_time,
                            t2.username,
                            t2.avater,
                            t3.user_id AS reply_user_id
                        FROM social_comment t1
                        LEFT JOIN user t2 ON t1.user_id COLLATE utf8mb4_unicode_ci = t2.id
                        LEFT JOIN social_comment t3 ON t1.parent_id = t3.id
                        WHERE t1.relation_id = :circle_id
                          AND t1.top_id IS NULL
                          AND t1.type = 'MUSIC_CIRCLE'
                    ) t4
                    LEFT JOIN user t5 ON t4.reply_user_id COLLATE utf8mb4_unicode_ci = t5.id
                ) t6
                LEFT JOIN (
                    SELECT parent_id, COUNT(parent_id) AS cnt
                    FROM social_comment
                    WHERE parent_id IS NOT NULL
                    GROUP BY parent_id
                ) t7 ON t6.id = t7.parent_id
                ORDER BY t6.create_time DESC
            """
            rows = self.db.execute(text(sql), {"circle_id": circle_id}).mappings().all()

            comment_list = []
            for row in rows:
                item = self._row_to_dict(row)
                item["reply_list"] = self.get_social_reply_parent_id(row["id"])
                comment_list.append(item)

            return comment_list
        except Exception as e:
            logger.error(f"获取朋友圈评论列表失败: {str(e)}", exc_info=True)
            return []

    def get_social_reply_parent_id(self, parent_id: int) -> List[Dict[str, Any]]:
        """获取某条一级评论的回复列表（前5条）"""
        try:
            sql = """
                SELECT
                    t6.id,
                    t6.content,
                    t6.parent_id,
                    t6.top_id,
                    t6.relation_id,
                    t6.type,
                    t6.user_id,
                    t6.create_time,
                    t6.update_time,
                    t6.username,
                    t6.avater,
                    t6.reply_user_id,
                    t6.reply_user_name
                FROM (
                    SELECT
                        t4.id,
                        t4.content,
                        t4.parent_id,
                        t4.top_id,
                        t4.relation_id,
                        t4.type,
                        t4.user_id,
                        t4.create_time,
                        t4.update_time,
                        t4.username,
                        t4.avater,
                        t4.reply_user_id,
                        t5.username AS reply_user_name
                    FROM (
                        SELECT
                            t1.id,
                            t1.content,
                            t1.parent_id,
                            t1.top_id,
                            t1.relation_id,
                            t1.type,
                            t1.user_id,
                            t1.create_time,
                            t1.udate_time AS update_time,
                            t2.username,
                            t2.avater,
                            t3.user_id AS reply_user_id
                        FROM social_comment t1
                        LEFT JOIN user t2 ON t1.user_id COLLATE utf8mb4_unicode_ci = t2.id
                        LEFT JOIN social_comment t3 ON t1.parent_id = t3.id
                        WHERE t1.parent_id = :parent_id
                    ) t4
                    LEFT JOIN user t5 ON t4.reply_user_id COLLATE utf8mb4_unicode_ci = t5.id
                ) t6
                ORDER BY t6.create_time DESC
                LIMIT 5
            """
            rows = self.db.execute(text(sql), {"parent_id": parent_id}).mappings().all()
            return [self._row_to_dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取朋友圈回复列表失败: {str(e)}", exc_info=True)
            return []

    def get_circle_article_count(self, circle_id: int) -> Dict[str, Any]:
        """
        获取文章的评论数、收藏数、浏览数

        说明：Spring 原始 SQL 引用了 `comment` 和 `circle_favorite` 两张表，
        但当前数据库中这两张表不存在（评论实际存储在 social_comment，
        点赞/收藏实际存储在 social_like，浏览记录在 circle_record）。
        因此这里映射到实际存在的表，保证接口可用：
        - commentCount  -> social_comment (type='MUSIC_CIRCLE')
        - favoriteCount -> social_like   (type='MUSIC_CIRCLE')
        - viewCount     -> circle_record (distinct user_id)
        """
        try:
            sql = """
                SELECT
                    CAST((SELECT COUNT(*) FROM social_comment
                          WHERE type = 'MUSIC_CIRCLE' AND relation_id = :circle_id) AS CHAR) AS comment_count,
                    CAST((SELECT COUNT(*) FROM social_like
                          WHERE type = 'MUSIC_CIRCLE' AND relation_id = :circle_id) AS CHAR) AS favorite_count,
                    CAST((SELECT COUNT(DISTINCT user_id) FROM circle_record
                          WHERE circle_id = :circle_id) AS CHAR) AS view_count
            """
            row = self.db.execute(text(sql), {"circle_id": circle_id}).mappings().first()
            if row:
                return dict(row)
            return {"comment_count": "0", "favorite_count": "0", "view_count": "0"}
        except Exception as e:
            logger.error(f"获取朋友圈文章计数失败: {str(e)}", exc_info=True)
            raise

    def get_circle_by_last_update_time(self, last_update_time: str, circle_type: str) -> int:
        """获取指定时间之后新增的朋友圈数量"""
        try:
            sql = "SELECT COUNT(id) FROM circle WHERE `type` = :type AND create_time > :last_update_time"
            result = self.db.execute(
                text(sql),
                {"type": circle_type, "last_update_time": last_update_time}
            ).scalar()
            return result or 0
        except Exception as e:
            logger.error(f"获取朋友圈最近更新数量失败: {str(e)}", exc_info=True)
            return 0

    # ==================== 写入 ====================

    def insert_circle(self, circle: Circle) -> Circle:
        """新增朋友圈记录"""
        try:
            self.db.add(circle)
            self.db.commit()
            self.db.refresh(circle)
            return circle
        except Exception as e:
            self.db.rollback()
            logger.error(f"插入朋友圈失败: {str(e)}", exc_info=True)
            raise

    # ==================== 工具 ====================

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        """将查询结果行转为字典，并格式化 datetime 字段"""
        item = dict(row)
        for key, value in item.items():
            if isinstance(value, datetime):
                item[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        return item
