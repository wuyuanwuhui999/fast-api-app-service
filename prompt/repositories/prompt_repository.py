import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text
from fastapi.logger import logger

from common.utils.result_util import ResultEntity
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptSchema, UpdatePromptSchema


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

    async def get_prompt_by_id(self, prompt_id: str, tenant_id: str) -> Optional[PromptSchema]:
        """
        根据ID和租户ID查询提示词记录（用于权限验证）
        
        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID
            
        Returns:
            Optional[PromptSchema]: 提示词记录
        """
        try:
            prompt = self.db.query(PromptModel).filter(
                PromptModel.id == prompt_id,
                PromptModel.tenant_id == tenant_id
            ).first()
            
            if prompt:
                return PromptSchema.model_validate(prompt)
            return None
            
        except Exception as e:
            logger.error(f"根据ID查询提示词失败: {str(e)}", exc_info=True)
            return None

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