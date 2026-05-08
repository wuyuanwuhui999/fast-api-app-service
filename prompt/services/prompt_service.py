from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptSchema
from prompt.repositories.prompt_repository import PromptRepository


class PromptService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = PromptRepository(db)

    async def get_prompt(self, tenant_id: str, current_user) -> ResultEntity:
        """
        根据租户ID查询提示词记录，如果不存在则创建默认提示词
        
        Args:
            tenant_id: 租户ID
            current_user: 当前登录用户
            
        Returns:
            ResultEntity: 提示词记录
        """
        try:
            # 验证租户ID
            if not tenant_id:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)
            
            # 查询提示词
            prompt = await self.repository.get_prompt_by_tenant(tenant_id)
            
            # 如果没有查到数据，则创建默认提示词
            if not prompt:
                logger.info(f"租户 {tenant_id} 未找到提示词，正在创建默认提示词...")
                prompt = await self.repository.create_default_prompt(tenant_id, current_user.id)
                
                if not prompt:
                    return ResultUtil.fail(msg="创建默认提示词失败", data=None)
                
                return ResultUtil.success(data=prompt, msg="已创建默认提示词")
            
            return ResultUtil.success(data=prompt)
            
        except Exception as e:
            logger.error(f"获取提示词失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取提示词失败: {str(e)}", data=None)