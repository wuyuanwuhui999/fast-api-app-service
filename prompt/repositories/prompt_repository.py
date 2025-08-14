from typing import Optional, List
from sqlalchemy.orm import Session

from prompt.models.prompt_model import PromptModel


class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_prompt_by_id(self, id: str) -> Optional[PromptModel]:
        return self.db.query().filter(PromptModel.id == id).first()

    def get_all_prompt(self, skip: int = 0, limit: int = 100) -> List[PromptModel]:
        return self.db.query(PromptModel).offset(skip).limit(limit).all()

    def create_prompt(self, entity: PromptModel) -> PromptModel:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def update_prompt_by_id(self, id: str, update_data: dict) -> Optional[PromptModel]:
        entity = self.get_prompt_by_id(id)
        if entity:
            for key, value in update_data.items():
                setattr(entity, key, value)
            self.db.commit()
            self.db.refresh(entity)
        return entity

    def delete_prompt_by_id(self, id: str) -> bool:
        entity = self.get_prompt_by_id(id)
        if entity:
            self.db.delete(entity)
            self.db.commit()
            return True
        return False
