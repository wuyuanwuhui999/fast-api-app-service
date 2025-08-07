import os
import uuid
import logging
from fastapi import UploadFile, HTTPException, Depends
from typing import Any
# from langchain import (
#     EmbeddingModel,
#     ElasticsearchEmbeddingStore,
#     TextSegment,
#     Embedding,
#     EmbeddingSearchRequest,
#     Filter,
#     IsEqualTo
# )
from sqlalchemy.orm import Session

from chat.repositories.chat_repository import ChatRepository
from common.config.common_config import get_settings
from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
import redis

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatService:
    def __init__(
            self,
            # embedding_model: EmbeddingModel,
            # elasticsearch_store: ElasticsearchEmbeddingStore,
            # qwen_assistant: Any,
            # deepseek_assistant: Any,
            db: Session = Depends(get_db)
    ):
        # self.embedding_model = embedding_model
        # self.elasticsearch_store = elasticsearch_store
        # self.qwen_assistant = qwen_assistant
        # self.deepseek_assistant = deepseek_assistant
        self.redis = redis.Redis.from_url(settings.redis_url)
        self.upload_dir = settings.UPLOAD_DIR
        self.chat_repository = ChatRepository(db)

    async def get_model_list(self) -> ResultEntity:
        return ResultUtil.success(data=self.chat_repository.get_model_list())

    # async def chat(self, user_id: str, chat_params: ChatParamsEntity):
    #     chat_entity = ChatEntity(
    #         user_id=user_id,
    #         chat_id=chat_params.chat_id,
    #         prompt=chat_params.prompt,
    #         model_name=chat_params.model_name,
    #         content=""
    #     )
    #
    #     response_collector = []
    #
    #     async for response_part in self.chat_with_websocket(user_id, chat_params):
    #         response_collector.append(response_part)
    #         chat_entity.content = "".join(response_collector)
    #
    #     # Save final chat
    #     chat_entity.content = "".join(response_collector)
    #     await self._save_chat(chat_entity)
    #
    #     return response_collector
    #
    # async def chat_with_websocket(self, user_id: str, chat_params: ChatParamsEntity):
    #     chat_entity = ChatEntity(
    #         user_id=user_id,
    #         chat_id=chat_params.chat_id,
    #         prompt=chat_params.prompt,
    #         model_name=chat_params.model_name
    #     )
    #
    #     if chat_params.type == "document":
    #         context = await self._build_context(
    #             chat_params.prompt,
    #             user_id,
    #             chat_params.directory_id
    #         )
    #         if not context:
    #             yield "对不起，没有查询到相关文档"
    #             return
    #         chat_params.prompt = context
    #
    #     assistant = self._select_assistant(chat_params.model_name)
    #
    #     try:
    #         async for response in assistant.stream_chat(chat_params):
    #             yield response
    #     except Exception as e:
    #         logger.error(f"Chat streaming error: {str(e)}")
    #         raise HTTPException(status_code=500, detail="Chat streaming failed")
    #
    async def delete_document(self, doc_id: str, user_id: str, directory_id: str):
        doc = await self._get_doc_by_id(doc_id, user_id, directory_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在或无权删除")

        # Delete from filesystem
        file_path = os.path.join(
            self.upload_dir,
            f"{doc.id}{'.' + doc.ext if doc.ext else ''}"
        )
        if os.path.exists(file_path):
            os.remove(file_path)

        # Delete from Elasticsearch
        directory_filter = IsEqualTo("metadata.directory_id", directory_id)
        user_filter = IsEqualTo("metadata.user_id", user_id)
        combined_filter = Filter.and_(directory_filter, user_filter)
        await self.elasticsearch_store.remove_all(combined_filter)

        # Delete from DB
        await self._delete_doc(doc_id, user_id, directory_id)

        return {"status": "success", "message": "文档删除成功"}
    #
    async def get_chat_history(self, user_id: str, page: int = 1, size: int = 10) -> ResultEntity:
        start = (page - 1) * size
        chat_history_list = self.chat_repository.get_chat_history(user_id, start, size)
        total = self.chat_repository.get_chat_history_total(user_id)
        return ResultUtil.success(data=chat_history_list, total=total)


    async def upload_doc(self, file: UploadFile, user_id: str, directory_id: str):
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        ext = self._get_file_extension(file.filename)
        if ext.lower() not in ["pdf", "txt"]:
            raise HTTPException(status_code=400, detail="只能上传pdf和txt的文档")

        doc_id = str(uuid.uuid4()).replace("-", "")

        try:
            content = await file.read()

            if ext.lower() == "pdf":
                await self._process_pdf(content, file.filename, user_id, doc_id, directory_id)
            else:
                await self._process_txt(content, file.filename, user_id, doc_id, directory_id)

            # Save file
            file_path = os.path.join(self.upload_dir, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

            # Save doc metadata
            doc = ChatDocEntity(
                id=doc_id,
                user_id=user_id,
                name=file.filename,
                ext=ext,
                directory_id=directory_id
            )
            await self._save_doc(doc)

            return {"status": "success", "message": "文件上传成功"}

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    # Helper methods would be implemented here...
