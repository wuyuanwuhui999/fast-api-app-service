from sqlalchemy.orm import Session
from typing import List

from chat.models import ChatModel
from chat.schemas import ChatSchema


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_model_list(self) -> List[ChatSchema]:
        db_models = self.db.query(ChatModel).all()
        return [ChatSchema.model_validate(model) for model in db_models]
