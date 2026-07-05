# prompt/repositories/prompt_repository.py
import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, desc, func
from fastapi.logger import logger

from common.utils.result_util import ResultEntity
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptSchema, UpdatePromptSchema, InsertPromptSchema


class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    async def get_prompt_by_tenant(self, tenant_id: str) -> Optional[PromptSchema]:
        """
        根据租户ID查询一条提示词记录

        Args:
            tenant_id: 租户ID

        Returns:
            Optional[PromptSchema]: 提示词记录，如果不存在则返回None
        """
        try:
            prompt = self.db.query(PromptModel).filter(
                PromptModel.tenant_id == tenant_id
            ).first()

            if prompt:
                return PromptSchema.model_validate(prompt)
            return None

        except Exception as e:
            logger.error(f"查询提示词失败: {str(e)}", exc_info=True)
            return None

    async def get_prompt_by_id(
            self,
            prompt_id: str,
            tenant_id: str,
            user_id: Optional[str] = None
    ) -> Optional[PromptSchema]:
        """
        根据ID和租户ID查询提示词记录（用于权限验证）

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID
            user_id: 用户ID（可选），用于权限校验

        Returns:
            Optional[PromptSchema]: 提示词记录
        """
        try:
            query = self.db.query(PromptModel).filter(
                PromptModel.id == prompt_id,
                PromptModel.tenant_id == tenant_id
            )

            # 如果传入了 user_id，校验用户权限
            if user_id:
                query = query.filter(PromptModel.user_id == user_id)

            prompt = query.first()

            if prompt:
                return PromptSchema.model_validate(prompt)
            return None

        except Exception as e:
            logger.error(f"根据ID查询提示词失败: {str(e)}", exc_info=True)
            return None

    async def get_prompt_by_id_only(self, prompt_id: str) -> Optional[PromptSchema]:
        """
        仅根据ID查询提示词记录（不校验租户和用户）
        用于查询单条提示词详情

        Args:
            prompt_id: 提示词ID

        Returns:
            Optional[PromptSchema]: 提示词记录
        """
        try:
            prompt = self.db.query(PromptModel).filter(
                PromptModel.id == prompt_id
            ).first()

            if prompt:
                return PromptSchema.model_validate(prompt)
            return None

        except Exception as e:
            logger.error(f"根据ID查询提示词失败: {str(e)}", exc_info=True)
            return None

    async def get_prompt_list_by_tenant(
            self,
            tenant_id: str,
            user_id: str,
            keyword: Optional[str] = None,
            page: int = 1,
            page_size: int = 10
    ) -> Tuple[List[PromptSchema], int]:
        """
        根据租户ID分页查询提示词列表（按更新时间倒序）
        支持按关键词模糊搜索提示词内容

        Args:
            tenant_id: 租户ID
            user_id: 当前用户ID（用于权限验证）
            keyword: 搜索关键词（可选），对 prompt 字段进行模糊匹配
            page: 页码，从1开始
            page_size: 每页数量

        Returns:
            Tuple[List[PromptSchema], int]: (提示词列表, 总记录数)
        """
        try:
            # 构建基础查询
            query = self.db.query(PromptModel).filter(
                PromptModel.tenant_id == tenant_id,
                PromptModel.user_id == user_id
            )

            # 如果有关键词，添加模糊搜索条件
            if keyword and keyword.strip():
                search_pattern = f"%{keyword.strip()}%"
                query = query.filter(PromptModel.prompt.like(search_pattern))

            # 查询总数
            total = query.count()

            # 分页查询
            offset = (page - 1) * page_size
            prompts = query.order_by(desc(PromptModel.update_time)).offset(offset).limit(page_size).all()

            return [PromptSchema.model_validate(prompt) for prompt in prompts], total

        except Exception as e:
            logger.error(f"查询提示词列表失败: {str(e)}", exc_info=True)
            return [], 0

    async def insert_prompt(
            self,
            prompt_text: str,
            tenant_id: str,
            user_id: str
    ) -> Optional[PromptSchema]:
        """
        插入新提示词

        Args:
            prompt_text: 提示词内容
            tenant_id: 租户ID
            user_id: 当前用户ID

        Returns:
            Optional[PromptSchema]: 创建的提示词记录
        """
        try:
            # 生成32位UUID（去掉横线）
            prompt_id = uuid.uuid4().hex
            current_time = datetime.now()

            db_prompt = PromptModel(
                id=prompt_id,
                prompt=prompt_text,
                tenant_id=tenant_id,
                user_id=user_id,
                create_time=current_time,
                update_time=current_time
            )

            self.db.add(db_prompt)
            self.db.commit()
            self.db.refresh(db_prompt)

            return PromptSchema.model_validate(db_prompt)

        except Exception as e:
            self.db.rollback()
            logger.error(f"插入提示词失败: {str(e)}", exc_info=True)
            return None

    async def delete_prompt_by_id(
            self,
            prompt_id: str,
            tenant_id: str,
            user_id: str
    ) -> bool:
        """
        根据ID删除提示词（需要验证租户和用户权限）

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID
            user_id: 当前用户ID

        Returns:
            bool: 是否删除成功
        """
        try:
            # 先查询验证权限
            prompt = self.db.query(PromptModel).filter(
                PromptModel.id == prompt_id,
                PromptModel.tenant_id == tenant_id,
                PromptModel.user_id == user_id
            ).first()

            if not prompt:
                return False

            self.db.delete(prompt)
            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除提示词失败: {str(e)}", exc_info=True)
            return False

    async def update_prompt(self, prompt_data: UpdatePromptSchema, user_id: str) -> Optional[PromptSchema]:
        """
        更新提示词记录

        Args:
            prompt_data: 更新提示词请求数据
            user_id: 当前操作用户ID

        Returns:
            Optional[PromptSchema]: 更新后的提示词记录
        """
        try:
            # 查询要更新的记录
            prompt = self.db.query(PromptModel).filter(
                PromptModel.id == prompt_data.id,
                PromptModel.tenant_id == prompt_data.tenant_id
            ).first()

            if not prompt:
                logger.warning(f"未找到提示词记录: id={prompt_data.id}, tenant_id={prompt_data.tenant_id}")
                return None

            # 更新字段
            prompt.prompt = prompt_data.prompt
            prompt.user_id = user_id  # 更新操作用户ID
            prompt.update_time = datetime.now()

            self.db.commit()
            self.db.refresh(prompt)

            return PromptSchema.model_validate(prompt)

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新提示词失败: {str(e)}", exc_info=True)
            return None

    async def create_default_prompt(self, tenant_id: str, user_id: str) -> Optional[PromptSchema]:
        """
        创建默认提示词记录

        Args:
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            Optional[PromptSchema]: 创建的提示词记录
        """
        try:
            default_prompt_text = "你叫小吴同学，是一个无所不能的AI助手，上知天文下知地理，请用小吴同学的身份回答问题。"

            # 生成32位UUID（去掉横线）
            prompt_id = uuid.uuid4().hex  # 生成32位UUID，不含横线
            current_time = datetime.now()

            db_prompt = PromptModel(
                id=prompt_id,
                prompt=default_prompt_text,
                tenant_id=tenant_id,
                user_id=user_id,
                create_time=current_time,
                update_time=current_time
            )

            self.db.add(db_prompt)
            self.db.commit()
            self.db.refresh(db_prompt)

            return PromptSchema.model_validate(db_prompt)

        except Exception as e:
            self.db.rollback()
            logger.error(f"创建默认提示词失败: {str(e)}", exc_info=True)
            return None