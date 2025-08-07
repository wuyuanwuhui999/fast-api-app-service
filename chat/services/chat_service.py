import os
import uuid
import logging
from fastapi import UploadFile, HTTPException, Depends
from langchain_community.embeddings import DashScopeEmbeddings, OpenAIEmbeddings
from sqlalchemy.orm import Session
from chat.repositories.chat_repository import ChatRepository
from chat.schemas.chat_schema import ChatDocSchema
from chat.utils.chat_util import PromptUtil
from common.config.common_config import get_settings
from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
import redis
from langchain.chat_models import init_chat_model
from PyPDF2 import PdfReader
from langchain_community import vectorstores
from langchain import embeddings, text_splitter
from langchain_community.vectorstores import ElasticsearchStore
from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchStore
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.documents import Document

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatService:
    def __init__(
            self,
            db: Session = Depends(get_db)
    ):

        self.elasticsearch_store = ElasticsearchStore(
            es_url="http://localhost:9200",  # 使用API代理服务提高访问稳定性
            index_name="chat_vector_index",
            embedding=OpenAIEmbeddings(model="mxbai-embed-large:latest"),
        )

        self.redis = redis.Redis.from_url(settings.redis_url)
        self.upload_dir = settings.UPLOAD_DIR
        self.chat_repository = ChatRepository(db)

    async def process_text_content(
            self,
            content: str,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str
    ):
        from langchain.schema import Document  # Import Document class
        from langchain.text_splitter import CharacterTextSplitter

        text_splitter = CharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )

        texts = text_splitter.split_text(content)

        documents = []
        for i, text in enumerate(texts):
            documents.append(Document(
                page_content=text,
                metadata={
                    "filename": filename,
                    "page": i + 1,
                    "user_id": user_id,
                    "doc_id": doc_id,
                    "directory_id": directory_id
                }
            ))

        await self.elasticsearch_store.add_documents(documents)

    async def process_pdf(
            self,
            content: bytes,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str
    ):
        """Process PDF file and store embeddings"""
        try:
            pdf_reader = PdfReader(os.io.BytesIO(content))
            full_text = ""

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                page_text = page.extract_text()
                if page_text:
                    full_text += f"Page {page_num}:\n{page_text}\n\n"

            await self.process_text_content(
                full_text,
                filename,
                user_id,
                doc_id,
                directory_id
            )
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")

    async def process_txt(
            self,
            content: bytes,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str
    ):
        """Process TXT file and store embeddings"""
        try:
            text_content = content.decode('utf-8')
            await self.process_text_content(
                text_content,
                filename,
                user_id,
                doc_id,
                directory_id
            )
        except Exception as e:
            logger.error(f"TXT processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"TXT处理失败: {str(e)}")

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
        doc = await self.chat_repository.get_doc_by_id(doc_id, user_id, directory_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在或无权删除")

        # Delete from filesystem
        file_path = os.path.join(
            self.upload_dir,
            f"{doc.id}{'.' + doc.ext if doc.ext else ''}"
        )
        if os.path.exists(file_path):
            os.remove(file_path)

        # directory_filter = IsEqualTo("metadata.directory_id", directory_id)
        # user_filter = IsEqualTo("metadata.user_id", user_id)
        # combined_filter = Filter.and_(directory_filter, user_filter)
        # await self.elasticsearch_store.remove_all(combined_filter)

        # Delete from DB
        await self.chat_repository.delete_doc(doc_id, user_id, directory_id)

        return ResultUtil.success(msg="文档删除成功")

    #
    async def get_chat_history(self, user_id: str, page: int = 1, size: int = 10) -> ResultEntity:
        start = (page - 1) * size
        chat_history_list = self.chat_repository.get_chat_history(user_id, start, size)
        total = self.chat_repository.get_chat_history_total(user_id)
        return ResultUtil.success(data=chat_history_list, total=total)

    async def upload_doc(self, file: UploadFile, user_id: str, directory_id: str) -> ResultEntity:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        ext = PromptUtil.get_file_extension(file.filename)
        if ext.lower() not in ["pdf", "txt"]:
            raise HTTPException(status_code=400, detail="只能上传pdf和txt的文档")

        doc_id = str(uuid.uuid4()).replace("-", "")

        try:
            content = await file.read()

            if ext.lower() == "pdf":
                await self.process_pdf(content, file.filename, user_id, doc_id, directory_id)
            else:
                await self.process_txt(content, file.filename, user_id, doc_id, directory_id)

            file_path = os.path.join(self.upload_dir, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

            doc = ChatDocSchema(
                id=doc_id,
                user_id=user_id,
                name=file.filename,
                ext=ext,
                directory_id=directory_id
            )
            await self.chat_repository.save_doc(doc)

            return ResultUtil.success(msg="文件上传成功")

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")