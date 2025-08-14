from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session

from common.config.common_database import get_db
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptCreateSchema, PromptUpdateSchema, Prompt
from prompt.repositories.prompt_repository import PromptRepository


class PromptService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = PromptRepository(db)

    def get_prompt(self, prompt_id: str) -> Optional[Prompt]:
        prompt = self.repository.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt not found"
            )
        return prompt

    def get_prompts(self, skip: int = 0, limit: int = 100) -> List[Prompt]:
        return self.repository.get_all_prompt(skip, limit)

    def create_prompt(self, prompt_create: PromptCreateSchema) -> Prompt:
        # 可以在这里添加业务逻辑验证
        prompt = PromptModel(**prompt_create.model_dump())
        return self.repository.create_prompt(prompt)

    def update_prompt(self, prompt_id: str, prompt_update: PromptUpdateSchema) -> Optional[Prompt]:
        existing_prompt = self.get_prompt(prompt_id)
        if not existing_prompt:
            return None

        update_data = prompt_update.model_dump(exclude_unset=True)
        return self.repository.update_prompt_by_id(prompt_id, update_data)

    def delete_prompt(self, prompt_id: str) -> bool:
        existing_prompt = self.get_prompt(prompt_id)
        if not existing_prompt:
            return False
        return self.repository.delete_prompt_by_id(prompt_id)

    def search_prompts(self, keyword: str, skip: int = 0, limit: int = 100) -> List[Prompt]:
        # 这里可以实现更复杂的搜索逻辑
        prompts = self.repository.get_all_prompt(skip, limit)
        return [p for p in prompts if keyword.lower() in p.title.lower() or
                (p.content and keyword.lower() in p.content.lower())]