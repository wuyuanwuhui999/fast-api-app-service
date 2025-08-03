from sqlalchemy.orm import Session
from typing import List

from chat.models import ChatModel


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_model_list(self) -> List[ChatModel]:
        return self.db.query(ChatModel).all()
