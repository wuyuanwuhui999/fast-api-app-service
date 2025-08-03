from sqlalchemy.orm import Session
from typing import List

from chat.models import ChatModel, ChatHistory
from chat.schemas import ChatModelSchema, ChatSchema


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_model_list(self) -> List[ChatModelSchema]:
        model_list = self.db.query(ChatModel).all()
        return [ChatModelSchema.model_validate(model).dict() for model in model_list]

    def get_chat_history(self,user_id:str, start:int, size:int)-> List[ChatSchema]:
        chat_history_list = self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id).limit(start,size)
        return [ChatSchema.model_validate(model).dict() for model in chat_history_list]

    def get_chat_history_total(self,user_id)->int:
         return self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id).count()

