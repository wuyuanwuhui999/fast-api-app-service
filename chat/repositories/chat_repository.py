from datetime import datetime

from elasticsearch.esql import and_
from fastapi.logger import logger
from sqlalchemy.orm import Session
from typing import List, Optional

from chat.models.chat_model import ChatModel, ChatHistory, ChatDocModel
from chat.schemas.chat_schema import ChatModelSchema, ChatSchema, ChatDocSchema
from chat.schemas.chat_schema import DirectorySchema


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_model_list(self) -> List[ChatModelSchema]:
        model_list = self.db.query(ChatModel).all()
        return [ChatModelSchema.model_validate(model).dict() for model in model_list]

    async def save_chat_history(self, chat_data: ChatSchema) -> bool:
        """保存聊天记录到数据库"""
        try:
            if not self.db:
                logger.error("数据库会话不可用")
                return False

            # 创建数据库对象（修正缩进位置）
            db_chat = ChatHistory(
                user_id=chat_data.user_id,
                model_name=chat_data.model_name,
                chat_id=chat_data.chat_id,
                prompt=chat_data.prompt,
                think_content=chat_data.think_content,
                response_content=chat_data.response_content,
                content=chat_data.content,
                create_time=datetime.now()
            )

            self.db.add(db_chat)
            await self.db.commit()
            return True

        except Exception as e:
            logger.error(f"保存失败: {str(e)}", exc_info=True)
            if self.db:  # 确保db存在才执行rollback
                await self.db.rollback()
            return False

        except Exception as e:
            logger.error(f"保存失败: {str(e)}")
            await self.db.rollback()
            return False

    def get_chat_history(self,user_id:str, start:int, size:int)-> List[ChatSchema]:
        chat_history_list = self.db.query(ChatHistory)\
            .filter(ChatHistory.user_id == user_id) \
            .offset(start) \
            .limit(size)
        return [
            ChatSchema.model_validate(
                {k: v for k, v in chat_item.__dict__.items() if not k.startswith('_')}
            ).dict() for chat_item in chat_history_list
        ]

    def get_chat_history_total(self,user_id)->int:
         return self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id).count()

    def save_doc(self, doc: ChatDocSchema) -> int:
        try:
            db_doc = ChatDocModel(
                id=doc.id,
                directory_id=doc.directory_id,
                name=doc.name,
                ext=doc.ext,
                tenant_id=doc.tenant_id,
                user_id=doc.user_id,
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            self.db.add(db_doc)
            self.db.commit()
            return 1
        except Exception as e:
            self.db.rollback()
            raise e

    def get_doc_by_id(
            self,
            doc_id: str,
            user_id: str,
            tenant_id: Optional[str] = None
    ) -> Optional[ChatDocSchema]:
        """Get document by ID with user and directory validation"""
        try:
            query = self.db.query(ChatDocModel).filter(
                ChatDocModel.id == doc_id,
                ChatDocModel.user_id == user_id,
            )

            doc = query.first()

            if doc:
                return ChatDocSchema(
                    id=doc.id,
                    directory_id=doc.directory_id,
                    name=doc.name,
                    ext=doc.ext,
                    user_id=doc.user_id,
                    tenant_id=doc.tenant_id,  # 新增
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
    ) -> bool:
        try:
            query = self.db.query(ChatDocModel).filter(
                and_(
                    ChatDocModel.id == doc_id,
                    ChatDocModel.user_id == user_id,
                )
            )
            deleted_count = query.delete()
            self.db.commit()
            return deleted_count > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise

    def get_doc_List(self, user_id: str, tenant_id: Optional[str] = None) -> List[ChatDocSchema]:
        query = self.db.query(ChatDocModel).filter(
            ChatDocModel.user_id == user_id,
            ChatDocModel.tenant_id == tenant_id
        )

        if tenant_id:
            query = query.filter(ChatDocModel.tenant_id == tenant_id)

        doc_list = query.all()

        return [
            ChatDocSchema.model_validate(
                {k: v for k, v in doc.__dict__.items() if not k.startswith('_')}
            ).dict() for doc in doc_list
        ]

    # 在ChatRepository类中修改create_directory方法
    async def create_directory(
            self,
            tenant_id: str,
            user_id: str,
            directory_name: str
    ) -> DirectorySchema:
        """在数据库中创建文件夹并返回完整的文件夹对象"""
        try:
            from chat.models.chat_model import ChatDocDirectory
            import uuid
            from datetime import datetime

            # 生成唯一的目录ID
            directory_id = str(uuid.uuid4()).replace("-", "")

            db_directory = ChatDocDirectory(
                id=directory_id,
                user_id=user_id,
                directory=directory_name,
                tenant_id=tenant_id,
                create_time=datetime.now(),
                update_time=datetime.now()
            )

            self.db.add(db_directory)
            self.db.commit()
            self.db.refresh(db_directory)  # 刷新以获取完整的对象数据

            # 返回完整的文件夹对象
            return DirectorySchema(
                id=db_directory.id,
                user_id=db_directory.user_id,
                directory=db_directory.directory,
                tenant_id=db_directory.tenant_id,
                create_time=db_directory.create_time.strftime(
                    "%Y-%m-%d %H:%M:%S") if db_directory.create_time else None,
                update_time=db_directory.update_time.strftime("%Y-%m-%d %H:%M:%S") if db_directory.update_time else None
            )

        except Exception as e:
            self.db.rollback()
            logger.error(f"数据库创建文件夹失败: {str(e)}")
            raise