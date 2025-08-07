from elasticsearch.esql import and_
from fastapi.logger import logger
from sqlalchemy.orm import Session
from typing import List, Optional

from chat.models.chat_model import ChatModel, ChatHistory, ChatDoc
from chat.schemas.chat_schema import ChatModelSchema, ChatSchema, ChatDocSchema


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

    def save_doc(self, doc: ChatDocSchema) -> bool:
        try:
            db_doc = ChatDoc(
                id=doc.id,
                directory_id=doc.directory_id,
                name=doc.name,
                ext=doc.ext,
                user_id=doc.user_id
            )
            self.db.add(db_doc)
            self.db.commit()
            return True
        except Exception as e:
            self.db.rollback()
            raise e

    def get_doc_by_id(
            self,
            doc_id: str,
            user_id: str,
            directory_id: str
    ) -> Optional[ChatDocSchema]:
        """Get document by ID with user and directory validation"""
        try:
            doc = self.db.query(ChatDoc).filter(
                ChatDoc.id == doc_id,
                ChatDoc.user_id == user_id,
                ChatDoc.directory_id == directory_id
            ).first()

            if doc:
                return ChatDocSchema(
                    id=doc.id,
                    directory_id=doc.directory_id,
                    name=doc.name,
                    ext=doc.ext,
                    user_id=doc.user_id,
                    create_time=doc.create_time,
                    update_time=doc.update_time
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {str(e)}")
            raise

    def delete_doc(
            self,
            doc_id: str,
            user_id: str,
            directory_id: str
    ) -> bool:
        try:
            deleted_count = self.db.query(ChatDoc).filter(
                and_(
                    ChatDoc.id == doc_id,
                    ChatDoc.user_id == user_id,
                    ChatDoc.directory_id == directory_id
                )
            ).delete()

            self.db.commit()
            return deleted_count > 0

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise

