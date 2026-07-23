# social/services/social_service.py
from typing import Optional, List, Dict, Any
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from social.repositories.social_repository import SocialRepository
from social.schemas.social_schema import InsertCommentSchema, CommentSchema, LikeRequestSchema


class SocialService:
    """社交服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.repository = SocialRepository(db)

    # ==================== 评论服务 ====================

    async def get_comment_count(self, relation_id: int, type: str) -> ResultEntity:
        """
        获取评论总数

        Args:
            relation_id: 关联资源ID
            type: 资源类型

        Returns:
            ResultEntity: 评论总数
        """
        try:
            if relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not type or not type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            count = self.repository.get_comment_count(relation_id, type)

            return ResultUtil.success(data=count)

        except Exception as e:
            logger.error(f"获取评论总数失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取评论总数失败: {str(e)}", data=None)

    async def get_top_comment_list(
            self,
            relation_id: int,
            type: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        获取一级评论列表（根评论）

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            page_num: 页码
            page_size: 每页数量

        Returns:
            ResultEntity: 评论列表
        """
        try:
            if relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not type or not type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            comment_list, total = self.repository.get_top_comments_with_pagination(
                relation_id=relation_id,
                type=type,
                page_num=page_num,
                page_size=page_size
            )

            return ResultUtil.success(data=comment_list, total=total)

        except Exception as e:
            logger.error(f"获取一级评论列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取评论列表失败: {str(e)}", data=None)

    async def get_reply_comment_list(
            self,
            top_id: int,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        获取回复列表（二级评论）

        Args:
            top_id: 顶级评论ID
            page_num: 页码
            page_size: 每页数量

        Returns:
            ResultEntity: 回复列表
        """
        try:
            if top_id <= 0:
                return ResultUtil.fail(msg="顶级评论ID不能为空", data=None)

            if page_num < 1:
                page_num = 1

            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            reply_list, total = self.repository.get_reply_list_by_top_id(
                top_id=top_id,
                page_num=page_num,
                page_size=page_size
            )

            return ResultUtil.success(data=reply_list, total=total)

        except Exception as e:
            logger.error(f"获取回复列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取回复列表失败: {str(e)}", data=None)

    async def insert_comment(
            self,
            comment_data: InsertCommentSchema,
            current_user_id: str
    ) -> ResultEntity:
        """
        新增评论/回复

        Args:
            comment_data: 评论数据
            current_user_id: 当前用户ID

        Returns:
            ResultEntity: 新增的评论
        """
        try:
            # 参数校验
            if not comment_data.content or not comment_data.content.strip():
                return ResultUtil.fail(msg="评论内容不能为空", data=None)

            if len(comment_data.content) > 500:
                return ResultUtil.fail(msg="评论内容不能超过500个字符", data=None)

            if comment_data.relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not comment_data.type or not comment_data.type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            # 如果是一级评论，parent_id 和 top_id 都传 0
            # 如果是回复，parent_id 和 top_id 根据实际情况传入
            parent_id = comment_data.parent_id if comment_data.parent_id else 0
            top_id = comment_data.top_id if comment_data.top_id else 0

            # 插入评论
            db_comment = self.repository.insert_comment(
                content=comment_data.content.strip(),
                parent_id=parent_id,
                top_id=top_id,
                relation_id=comment_data.relation_id,
                type=comment_data.type,
                user_id=current_user_id
            )

            if not db_comment:
                return ResultUtil.fail(msg="发表评论失败", data=None)

            # 获取完整的评论信息（含用户昵称、头像）
            comment_with_user = self.repository.get_comment_with_user(db_comment.id)
            if comment_with_user:
                # 如果是回复，获取被回复人昵称
                if comment_with_user.get("parent_id"):
                    parent_comment = self.repository.get_comment_by_id(comment_with_user["parent_id"])
                    if parent_comment:
                        parent_user = self.repository.db.query(UserMode).filter(
                            UserMode.id == parent_comment.user_id
                        ).first()
                        if parent_user:
                            comment_with_user["reply_user_name"] = parent_user.username

                return ResultUtil.success(data=comment_with_user, msg="评论成功")
            else:
                return ResultUtil.success(data=CommentSchema.model_validate(db_comment), msg="评论成功")

        except Exception as e:
            logger.error(f"新增评论失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"发表评论失败: {str(e)}", data=None)

    async def delete_comment(self, comment_id: int, current_user_id: str) -> ResultEntity:
        """
        删除评论（仅限评论所有者）

        Args:
            comment_id: 评论ID
            current_user_id: 当前用户ID

        Returns:
            ResultEntity: 删除结果
        """
        try:
            if comment_id <= 0:
                return ResultUtil.fail(msg="评论ID不能为空", data=None)

            # 检查评论是否存在
            comment = self.repository.get_comment_by_id(comment_id)
            if not comment:
                return ResultUtil.fail(msg="评论不存在", data=None)

            # 检查是否是评论所有者
            if comment.user_id != current_user_id:
                return ResultUtil.fail(msg="无权删除此评论", data=None)

            # 删除评论
            result = self.repository.delete_comment(comment_id, current_user_id)

            if result > 0:
                return ResultUtil.success(data=result, msg="删除成功")
            else:
                return ResultUtil.fail(msg="删除失败", data=None)

        except Exception as e:
            logger.error(f"删除评论失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"删除评论失败: {str(e)}", data=None)

    # ==================== 点赞服务 ====================

    async def save_like(self, like_data: LikeRequestSchema, current_user_id: str) -> ResultEntity:
        """
        添加点赞

        Args:
            like_data: 点赞请求数据
            current_user_id: 当前用户ID

        Returns:
            ResultEntity: 点赞结果
        """
        try:
            if like_data.relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not like_data.type or not like_data.type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            db_like = self.repository.save_like(
                relation_id=like_data.relation_id,
                type=like_data.type,
                user_id=current_user_id
            )

            if db_like is None:
                return ResultUtil.fail(msg="您已点赞过该资源", data=None)

            return ResultUtil.success(data=LikeSchema.model_validate(db_like), msg="点赞成功")

        except Exception as e:
            logger.error(f"添加点赞失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"点赞失败: {str(e)}", data=None)

    async def delete_like(self, relation_id: int, type: str, current_user_id: str) -> ResultEntity:
        """
        取消点赞

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            current_user_id: 当前用户ID

        Returns:
            ResultEntity: 取消结果
        """
        try:
            if relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not type or not type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            # 检查是否已点赞
            if not self.repository.is_like(relation_id, type, current_user_id):
                return ResultUtil.fail(msg="尚未点赞该资源", data=None)

            result = self.repository.delete_like(relation_id, type, current_user_id)

            if result > 0:
                return ResultUtil.success(data=result, msg="取消点赞成功")
            else:
                return ResultUtil.fail(msg="取消点赞失败", data=None)

        except Exception as e:
            logger.error(f"取消点赞失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"取消点赞失败: {str(e)}", data=None)

    async def is_like(self, relation_id: int, type: str, current_user_id: str) -> ResultEntity:
        """
        检查是否已点赞

        Args:
            relation_id: 关联资源ID
            type: 资源类型
            current_user_id: 当前用户ID

        Returns:
            ResultEntity: 点赞状态（1:已点赞，0:未点赞）
        """
        try:
            if relation_id <= 0:
                return ResultUtil.fail(msg="关联资源ID不能为空", data=None)

            if not type or not type.strip():
                return ResultUtil.fail(msg="资源类型不能为空", data=None)

            is_liked = self.repository.is_like(relation_id, type, current_user_id)

            return ResultUtil.success(data=1 if is_liked else 0)

        except Exception as e:
            logger.error(f"检查点赞状态失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"检查点赞状态失败: {str(e)}", data=None)