from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptCreateSchema, PromptUpdateSchema, Prompt, PromptCategorySchema
from prompt.repositories.prompt_repository import PromptRepository


class PromptService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = PromptRepository(db)

    async def get_prompt_category_list(self)->ResultEntity:
        return ResultUtil.success(data=self.repository.get_prompt_category_list())

    async def get_system_prompt_list_by_category(self, tenant_id: str, category_id:str, user_id:str, page_num:int, page_size:int)->ResultEntity:
        return ResultUtil.success(
            data=self.repository.get_system_prompt_list_by_category(tenant_id,category_id,user_id,page_num,page_size),
            total=self.repository.get_system_prompt_count_by_category(tenant_id,category_id,user_id)
        )

    async def insert_collect_prompt(self,tenant_id: str, prompt_id:str, user_id:str)->ResultEntity:
        return ResultUtil.success(data=self.repository.insert_collect_prompt(tenant_id,prompt_id,user_id))

    async def delete_collect_prompt(self,tenant_id: str, prompt_id:str, user_id:str)->ResultEntity:
        return ResultUtil.success(data=self.repository.delete_collect_prompt(tenant_id,prompt_id,user_id))

    async def get_my_collect_prompt_list(self,tenant_id: str, category_id:str, user_id:str, page_num:int, page_size:int)->ResultEntity:
        return ResultUtil.success(
            data=self.repository.get_my_collect_prompt_list(tenant_id,category_id,user_id,page_num,page_size),
            total=self.repository.get_my_collect_prompt_count(tenant_id,category_id,user_id)
        )