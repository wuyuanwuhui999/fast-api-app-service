from datetime import datetime

from elasticsearch.esql import and_
from fastapi.logger import logger
from sqlalchemy.orm import Session
from typing import List, Optional

from chat.models.chat_model import ChatModel, ChatHistory, ChatDocModel, ChatDocDirectory
from chat.schemas.chat_schema import ChatModelSchema, ChatSchema, ChatDocSchema
from chat.schemas.chat_schema import DirectorySchema


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_model_list(self, company_id: Optional[str] = None, keyword: Optional[str] = None) -> List[ChatModelSchema]:
        """获取模型列表，支持按企业ID筛选和关键词模糊搜索"""
        query = self.db.query(ChatModel).filter(ChatModel.disabled == 0)

        # 如果提供了 company_id，则按企业ID筛选
        if company_id:
            query = query.filter(ChatModel.company_id == company_id)

        # 如果提供了 keyword，按模型名称模糊搜索
        if keyword and keyword.strip():
            search_pattern = f"%{keyword.strip()}%"
            query = query.filter(ChatModel.model_name.like(search_pattern))

        # 按创建时间降序
        query = query.order_by(ChatModel.create_time.desc())

        model_list = query.all()
        return [ChatModelSchema.model_validate(model).model_dump(by_alias=True) for model in model_list]

    def get_model_by_id(self, model_id: str, company_id: Optional[str] = None) -> Optional[ChatModelSchema]:
        """根据模型ID获取模型配置，支持按企业ID筛选"""
        try:
            query = self.db.query(ChatModel).filter(
                ChatModel.id == model_id,
                ChatModel.disabled == 0
            )

            # 如果提供了 company_id，则按企业ID筛选
            if company_id:
                query = query.filter(ChatModel.company_id == company_id)

            model = query.first()
            if model:
                return ChatModelSchema.model_validate(model)
            return None
        except Exception as e:
            logger.error(f"获取模型配置失败: {str(e)}")
            return None

    def get_model_by_id_only(self, model_id: str) -> Optional[ChatModel]:
        """仅根据ID获取模型（不校验company_id），用于权限验证"""
        try:
            return self.db.query(ChatModel).filter(
                ChatModel.id == model_id,
                ChatModel.disabled == 0
            ).first()
        except Exception as e:
            logger.error(f"获取模型失败: {str(e)}")
            return None

    def add_model(
            self,
            model_name: str,
            model_type: str,
            company_id: str,
            base_url: str,
            created_by: str,
            api_key: Optional[str] = None
    ) -> Optional[ChatModelSchema]:
        """添加新模型"""
        try:
            import uuid

            db_model = ChatModel(
                id=str(uuid.uuid4()).replace("-", ""),
                model_name=model_name,
                type=model_type,
                company_id=company_id,
                base_url=base_url,
                api_key=api_key,
                created_by=created_by,
                disabled=0,
                create_time=datetime.now(),
                update_time=datetime.now()
            )

            self.db.add(db_model)
            self.db.commit()
            self.db.refresh(db_model)

            return ChatModelSchema.model_validate(db_model)

        except Exception as e:
            self.db.rollback()
            logger.error(f"添加模型失败: {str(e)}", exc_info=True)
            return None

    def update_model(
            self,
            model_id: str,
            model_name: str,
            model_type: str,
            company_id: str,
            base_url: str,
            api_key: Optional[str] = None
    ) -> Optional[ChatModelSchema]:
        """更新模型"""
        try:
            db_model = self.db.query(ChatModel).filter(
                ChatModel.id == model_id,
                ChatModel.disabled == 0
            ).first()

            if not db_model:
                return None

            db_model.model_name = model_name
            db_model.type = model_type
            db_model.company_id = company_id
            db_model.base_url = base_url
            db_model.api_key = api_key
            db_model.update_time = datetime.now()

            self.db.commit()
            self.db.refresh(db_model)

            return ChatModelSchema.model_validate(db_model)

        except Exception as e:
            self.db.rollback()
            logger.error(f"更新模型失败: {str(e)}", exc_info=True)
            return None

    def delete_model(self, model_id: str) -> bool:
        """删除模型（软删除）"""
        try:
            db_model = self.db.query(ChatModel).filter(
                ChatModel.id == model_id,
                ChatModel.disabled == 0
            ).first()

            if not db_model:
                return False

            db_model.disabled = 1
            db_model.update_time = datetime.now()

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            logger.error(f"删除模型失败: {str(e)}", exc_info=True)
            return False

    def check_user_is_admin(self, company_id: str, user_id: str) -> bool:
        """
        检查用户是否在指定企业内且角色 > 0（管理员及以上）
        使用原生SQL查询 company_user 表
        """
        try:
            from sqlalchemy import text

            sql = """
                  SELECT COUNT(*)
                  FROM company_user
                  WHERE company_id = :company_id
                    AND user_id = :user_id
                    AND status = 1
                    AND CAST(role AS UNSIGNED) > 0 \
                  """

            result = self.db.execute(
                text(sql),
                {"company_id": company_id, "user_id": user_id}
            )

            count = result.scalar()
            return count > 0

        except Exception as e:
            logger.error(f"检查用户管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def save_chat_history(self, chat_data: ChatSchema) -> bool:
        """保存聊天记录到数据库"""
        try:
            if not self.db:
                logger.error("数据库会话不可用")
                return False

            db_chat = ChatHistory(
                user_id=chat_data.user_id,
                tenant_id=chat_data.tenant_id,
                model_id=chat_data.model_id,
                chat_id=chat_data.chat_id,
                prompt=chat_data.prompt,
                system_prompt=chat_data.system_prompt,
                think_content=chat_data.think_content,
                response_content=chat_data.response_content,
                content=chat_data.content,
                create_time=datetime.now()
            )

            self.db.add(db_chat)
            self.db.commit()
            logger.info(f"聊天记录保存成功: user_id={chat_data.user_id}, chat_id={chat_data.chat_id}")
            return True

        except Exception as e:
            logger.error(f"保存聊天记录失败: {str(e)}", exc_info=True)
            if self.db:
                self.db.rollback()
            return False

    def get_chat_history(
            self,
            user_id: str,
            start: int,
            size: int,
            tenant_id: Optional[str] = None
    ) -> List[ChatSchema]:
        """
        获取用户的聊天历史记录

        Args:
            user_id: 用户ID
            start: 起始位置（偏移量）
            size: 每页数量
            tenant_id: 租户ID（可选），不传则查询所有租户
        """
        query = self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id)

        # 如果传入了 tenant_id，则按租户过滤
        if tenant_id is not None:
            query = query.filter(ChatHistory.tenant_id == tenant_id)

        chat_history_list = query.order_by(ChatHistory.create_time.desc()) \
            .offset(start) \
            .limit(size) \
            .all()

        return [
            ChatSchema(
                id=chat.id,
                user_id=chat.user_id,
                tenant_id=chat.tenant_id,
                model_id=chat.model_id,
                files=chat.files,
                chat_id=chat.chat_id,
                prompt=chat.prompt,
                system_prompt=chat.system_prompt,
                think_content=chat.think_content,
                response_content=chat.response_content,
                content=chat.content,
                create_time=chat.create_time
            ) for chat in chat_history_list
        ]

    def get_chat_history_total(
            self,
            user_id: str,
            tenant_id: Optional[str] = None
    ) -> int:
        """
        获取用户的聊天历史记录总数

        Args:
            user_id: 用户ID
            tenant_id: 租户ID（可选），不传则统计所有租户
        """
        query = self.db.query(ChatHistory).filter(ChatHistory.user_id == user_id)

        # 如果传入了 tenant_id，则按租户过滤
        if tenant_id is not None:
            query = query.filter(ChatHistory.tenant_id == tenant_id)

        return query.count()

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

            if tenant_id:
                query = query.filter(ChatDocModel.tenant_id == tenant_id)

            doc = query.first()

            if doc:
                return ChatDocSchema(
                    id=doc.id,
                    directory_id=doc.directory_id,
                    name=doc.name,
                    ext=doc.ext,
                    user_id=doc.user_id,
                    tenant_id=doc.tenant_id,
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
                ChatDocModel.id == doc_id,
                ChatDocModel.user_id == user_id,
            )
            deleted_count = query.delete()
            self.db.commit()
            return deleted_count > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            raise

    def get_doc_List(self, user_id: str, directory_id: Optional[str] = None) -> List[ChatDocSchema]:
        query = self.db.query(ChatDocModel).filter(
            ChatDocModel.user_id == user_id,
        )

        query = query.filter(ChatDocModel.directory_id == directory_id)

        doc_list = query.all()

        return [
            ChatDocSchema(
                id=doc.id,
                directory_id=doc.directory_id,
                name=doc.name,
                ext=doc.ext,
                user_id=doc.user_id,
                tenant_id=doc.tenant_id,
                create_time=doc.create_time,
                update_time=doc.update_time
            ) for doc in doc_list
        ]

    async def create_directory(
            self,
            tenant_id: str,
            user_id: str,
            directory_name: str
    ) -> DirectorySchema:
        """在数据库中创建文件夹并返回完整的文件夹对象"""
        try:
            import uuid
            from datetime import datetime

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
            self.db.refresh(db_directory)

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

    async def check_directory_exists(self, tenant_id: str, user_id: str, directory_name: str) -> bool:
        """检查文件夹是否已存在"""
        try:
            directory = self.db.query(ChatDocDirectory).filter(
                ChatDocDirectory.tenant_id == tenant_id,
                ChatDocDirectory.user_id == user_id,
                ChatDocDirectory.directory == directory_name
            ).first()
            return directory is not None
        except Exception as e:
            logger.error(f"检查文件夹是否存在失败: {str(e)}")
            return False

    def get_chat_history_by_chat_id(
            self,
            user_id: str,
            chat_id: str
    ) -> List[ChatSchema]:
        """根据会话ID获取聊天历史（按时间正序）"""
        chat_history_list = self.db.query(ChatHistory).filter(
            ChatHistory.user_id == user_id,
            ChatHistory.chat_id == chat_id
        ).order_by(ChatHistory.create_time.asc()).all()

        return [
            ChatSchema(
                id=chat.id,
                user_id=chat.user_id,
                tenant_id=chat.tenant_id,
                model_id=chat.model_id,
                files=chat.files,
                chat_id=chat.chat_id,
                prompt=chat.prompt,
                system_prompt=chat.system_prompt,
                think_content=chat.think_content,
                response_content=chat.response_content,
                content=chat.content,
                create_time=chat.create_time
            ) for chat in chat_history_list
        ]

    def get_doc_list_by_tenant(self, user_id: str, tenant_id: str) -> List[dict]:
        """获取指定租户下的文档列表（含目录名称）"""
        from sqlalchemy import text

        sql = """
            SELECT
                cd.id,
                cd.directory_id,
                cd.name,
                cd.ext,
                cd.user_id,
                cd.tenant_id,
                cd.create_time,
                cd.update_time,
                CASE WHEN cd.directory_id = 'default' THEN '默认文件夹' ELSE cdd.directory END AS directory_name
            FROM chat_doc cd
            LEFT JOIN chat_doc_directory cdd ON cd.directory_id = cdd.id
            WHERE cd.user_id = :user_id AND cd.tenant_id = :tenant_id
        """
        rows = self.db.execute(text(sql), {"user_id": user_id, "tenant_id": tenant_id}).mappings().all()

        result = []
        for row in rows:
            item = dict(row)
            for key, value in item.items():
                if isinstance(value, datetime):
                    item[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            result.append(item)
        return result

    def rename_directory(self, directory_id: str, user_id: str, new_name: str) -> bool:
        """重命名目录（校验归属）"""
        db_directory = self.db.query(ChatDocDirectory).filter(
            ChatDocDirectory.id == directory_id,
            ChatDocDirectory.user_id == user_id
        ).first()
        if db_directory:
            db_directory.directory = new_name
            db_directory.update_time = datetime.now()
            self.db.commit()
            return True
        return False

    def delete_directory(self, directory_id: str, user_id: str) -> bool:
        """删除目录（校验归属）"""
        result = self.db.query(ChatDocDirectory).filter(
            ChatDocDirectory.id == directory_id,
            ChatDocDirectory.user_id == user_id
        ).delete()
        self.db.commit()
        return result > 0