# social/repositories/social_repository.py
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, and_, or_, select, text
from fastapi.logger import logger

from common.models.common_model import UserMode
from social.models.social_model import SocialComment, SocialLike
from social.schemas.social_schema import CommentSchema, LikeSchema, InsertCommentSchema


class SocialRepository:
    """社交数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 评论相关 ====================

    def get_comment_count(self, relation_id: int, type: str) -> int:
        """
        获取评论总数

        Args:
            relation_id: 关联资源ID
            type: 资源类型

        Returns:
            int: 评论总数
        """
        try:
            count = self.db.query(func.count(SocialComment.id)).filter(
                SocialComment.relation_id == relation_id,
                SocialComment.type == type
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"获取评论总数失败: {str(e)}", exc_info=True)
            return 0

    def get_top_comments_with_pagination(
            self,
            relation_id: int,
            type: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取一级评论列表（根评论），包含回复统计和回复列表

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            page_num: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Dict], int]: (评论列表, 总记录数)
        """
        try:
            offset = (page_num - 1) * page_size

            # 构建基础查询：一级评论（parent_id IS NULL）
            query = self.db.query(
                SocialComment,
                UserMode.username,
                UserMode.avater
            ).outerjoin(
                UserMode,
                SocialComment.user_id == UserMode.id
            ).filter(
                SocialComment.relation_id == relation_id,
                SocialComment.type == type,
                SocialComment.parent_id.is_(None)
            )

            # 查询总数
            total_query = self.db.query(func.count(SocialComment.id)).filter(
                SocialComment.relation_id == relation_id,
                SocialComment.type == type,
                SocialComment.parent_id.is_(None)
            )
            total = total_query.scalar() or 0

            # 分页查询
            results = query.order_by(
                desc(SocialComment.create_time)
            ).offset(offset).limit(page_size).all()

            # 构建结果列表
            comment_list = []
            for comment, username, avater in results:
                # 获取回复总数
                reply_count = self.get_reply_count(comment.id)

                # 获取前5条回复
                reply_list = self.get_reply_list_by_top_id(comment.id, limit=5)

                comment_dict = {
                    "id": comment.id,
                    "content": comment.content,
                    "parent_id": comment.parent_id,
                    "top_id": comment.top_id,
                    "relation_id": comment.relation_id,
                    "type": comment.type,
                    "user_id": comment.user_id,
                    "username": username,
                    "avater": avater,
                    "reply_count": reply_count,
                    "reply_list": reply_list,
                    "reply_user_name": None,
                    "create_time": comment.create_time,
                    "update_time": comment.update_time
                }
                comment_list.append(comment_dict)

            return comment_list, total

        except Exception as e:
            logger.error(f"获取一级评论列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_reply_count(self, top_id: int) -> int:
        """
        获取指定顶级评论的回复总数

        Args:
            top_id: 顶级评论ID

        Returns:
            int: 回复总数
        """
        try:
            count = self.db.query(func.count(SocialComment.id)).filter(
                SocialComment.top_id == top_id
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"获取回复总数失败: {str(e)}", exc_info=True)
            return 0

    def get_reply_list_by_top_id(
            self,
            top_id: int,
            page_num: int = 1,
            page_size: int = 10
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        获取指定顶级评论的回复列表（分页），包含被回复人信息

        Args:
            top_id: 顶级评论ID
            page_num: 页码
            page_size: 每页数量

        Returns:
            Tuple[List[Dict], int]: (回复列表, 总记录数)
        """
        try:
            offset = (page_num - 1) * page_size

            # 查询回复列表，关联用户表获取评论者信息
            # 如果需要被回复人信息，需要再关联一次用户表（parent_id 对应的用户）
            results = self.db.query(
                SocialComment,
                UserMode.username.label("commenter_name"),
                UserMode.avater.label("commenter_avater"),
                # 被回复人：通过 parent_id 关联
                UserMode.username.label("reply_user_name")
            ).outerjoin(
                UserMode,
                SocialComment.user_id == UserMode.id
            ).outerjoin(
                UserMode,
                SocialComment.parent_id == UserMode.id
            ).filter(
                SocialComment.top_id == top_id
            ).order_by(
                desc(SocialComment.create_time)
            ).offset(offset).limit(page_size).all()

            # 查询总数
            total = self.db.query(func.count(SocialComment.id)).filter(
                SocialComment.top_id == top_id
            ).scalar() or 0

            # 构建结果列表
            reply_list = []
            for comment, commenter_name, commenter_avater, reply_user_name in results:
                # 如果 parent_id 不为 None，需要查询被回复人的昵称
                # 但由于 SQLAlchemy 的 alias 问题，我们单独查询
                reply_user_name_value = None
                if comment.parent_id:
                    parent_comment = self.db.query(SocialComment).filter(
                        SocialComment.id == comment.parent_id
                    ).first()
                    if parent_comment:
                        parent_user = self.db.query(UserMode).filter(
                            UserMode.id == parent_comment.user_id
                        ).first()
                        if parent_user:
                            reply_user_name_value = parent_user.username

                reply_dict = {
                    "id": comment.id,
                    "content": comment.content,
                    "parent_id": comment.parent_id,
                    "top_id": comment.top_id,
                    "relation_id": comment.relation_id,
                    "type": comment.type,
                    "user_id": comment.user_id,
                    "username": commenter_name,
                    "avater": commenter_avater,
                    "reply_count": 0,  # 回复的回复暂时不统计
                    "reply_list": [],
                    "reply_user_name": reply_user_name_value,
                    "create_time": comment.create_time,
                    "update_time": comment.update_time
                }
                reply_list.append(reply_dict)

            return reply_list, total

        except Exception as e:
            logger.error(f"获取回复列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_comment_by_id(self, comment_id: int) -> Optional[SocialComment]:
        """根据ID获取评论"""
        try:
            return self.db.query(SocialComment).filter(
                SocialComment.id == comment_id
            ).first()
        except Exception as e:
            logger.error(f"获取评论失败: {str(e)}", exc_info=True)
            return None

    def insert_comment(
            self,
            content: str,
            parent_id: int,
            top_id: int,
            relation_id: int,
            type: str,
            user_id: str
    ) -> Optional[SocialComment]:
        """
        新增评论

        Args:
            content: 评论内容
            parent_id: 父评论ID（0表示一级评论）
            top_id: 顶级评论ID（0表示一级评论）
            relation_id: 关联资源ID
            type: 资源类型
            user_id: 用户ID

        Returns:
            Optional[SocialComment]: 新增的评论对象
        """
        try:
            # 处理参数：将0转换为None
            parent_id_value = parent_id if parent_id > 0 else None
            top_id_value = top_id if top_id > 0 else None

            # 如果是回复（parent_id不为None），但top_id为None，需要自动设置top_id
            if parent_id_value is not None and top_id_value is None:
                # 查询父评论的top_id
                parent_comment = self.get_comment_by_id(parent_id_value)
                if parent_comment:
                    if parent_comment.top_id is not None:
                        top_id_value = parent_comment.top_id
                    else:
                        top_id_value = parent_comment.id

            db_comment = SocialComment(
                content=content,
                parent_id=parent_id_value,
                top_id=top_id_value,
                relation_id=relation_id,
                type=type,
                user_id=user_id
            )

            self.db.add(db_comment)
            self.db.commit()
            self.db.refresh(db_comment)

            return db_comment

        except Exception as e:
            self.db.rollback()
            logger.error(f"插入评论失败: {str(e)}", exc_info=True)
            return None

    def delete_comment(self, comment_id: int, user_id: str) -> int:
        """
        删除评论（仅限评论所有者）

        Args:
            comment_id: 评论ID
            user_id: 用户ID

        Returns:
            int: 删除的行数
        """
        try:
            result = self.db.query(SocialComment).filter(
                SocialComment.id == comment_id,
                SocialComment.user_id == user_id
            ).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除评论失败: {str(e)}", exc_info=True)
            return 0

    # ==================== 点赞相关 ====================

    def save_like(self, relation_id: int, type: str, user_id: str) -> Optional[SocialLike]:
        """
        添加点赞（使用 ORM 方式，先查询再插入）

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            user_id: 用户ID

        Returns:
            Optional[SocialLike]: 新增的点赞记录
        """
        try:
            # 先检查是否已存在
            existing = self.db.query(SocialLike).filter(
                SocialLike.relation_id == relation_id,
                SocialLike.type == type,
                SocialLike.user_id == user_id
            ).first()

            if existing:
                logger.info(f"用户 {user_id} 已点赞 {type}:{relation_id}")
                return None

            db_like = SocialLike(
                relation_id=relation_id,
                type=type,
                user_id=user_id
            )

            self.db.add(db_like)
            self.db.commit()
            self.db.refresh(db_like)

            return db_like

        except Exception as e:
            self.db.rollback()
            logger.error(f"添加点赞失败: {str(e)}", exc_info=True)
            return None

    def delete_like(self, relation_id: int, type: str, user_id: str) -> int:
        """
        取消点赞

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            user_id: 用户ID

        Returns:
            int: 删除的行数
        """
        try:
            result = self.db.query(SocialLike).filter(
                SocialLike.relation_id == relation_id,
                SocialLike.type == type,
                SocialLike.user_id == user_id
            ).delete()
            self.db.commit()
            return result
        except Exception as e:
            self.db.rollback()
            logger.error(f"取消点赞失败: {str(e)}", exc_info=True)
            return 0

    def is_like(self, relation_id: int, type: str, user_id: str) -> bool:
        """
        检查是否已点赞

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            user_id: 用户ID

        Returns:
            bool: 是否已点赞
        """
        try:
            count = self.db.query(func.count(SocialLike.id)).filter(
                SocialLike.relation_id == relation_id,
                SocialLike.type == type,
                SocialLike.user_id == user_id
            ).scalar()
            return count > 0
        except Exception as e:
            logger.error(f"检查点赞状态失败: {str(e)}", exc_info=True)
            return False

    def get_like_by_id(self, like_id: int) -> Optional[SocialLike]:
        """根据ID获取点赞记录"""
        try:
            return self.db.query(SocialLike).filter(
                SocialLike.id == like_id
            ).first()
        except Exception as e:
            logger.error(f"获取点赞记录失败: {str(e)}", exc_info=True)
            return None

    def get_comment_with_user(self, comment_id: int) -> Optional[Dict[str, Any]]:
        """
        获取评论及其用户信息

        Args:
            comment_id: 评论ID

        Returns:
            Optional[Dict]: 评论信息（含用户昵称、头像）
        """
        try:
            result = self.db.query(
                SocialComment,
                UserMode.username,
                UserMode.avater
            ).outerjoin(
                UserMode,
                SocialComment.user_id == UserMode.id
            ).filter(
                SocialComment.id == comment_id
            ).first()

            if not result:
                return None

            comment, username, avater = result
            return {
                "id": comment.id,
                "content": comment.content,
                "parent_id": comment.parent_id,
                "top_id": comment.top_id,
                "relation_id": comment.relation_id,
                "type": comment.type,
                "user_id": comment.user_id,
                "username": username,
                "avater": avater,
                "create_time": comment.create_time,
                "update_time": comment.update_time
            }
        except Exception as e:
            logger.error(f"获取评论用户信息失败: {str(e)}", exc_info=True)
            return None