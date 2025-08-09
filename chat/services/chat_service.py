import asyncio
import uuid
import logging
from fastapi import UploadFile, HTTPException, Depends
import pdfplumber
from sqlalchemy.orm import Session
import os
from chat.repositories.chat_repository import ChatRepository
from chat.schemas.chat_schema import ChatDocSchema, ChatParamsEntity
from chat.utils.chat_util import PromptUtil
from common.config.common_config import get_settings
from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
import redis
from langchain.chat_models import init_chat_model
from PyPDF2 import PdfReader
from langchain_community import vectorstores
from langchain import embeddings, text_splitter
from elasticsearch import Elasticsearch
from langchain_elasticsearch import ElasticsearchStore
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain.schema import Document  # Import Document class
from langchain.text_splitter import CharacterTextSplitter
from io import BytesIO
import elasticsearch_dsl

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
            embedding=OllamaEmbeddings(model="mxbai-embed-large:latest")
        )

        self.chat_model = OllamaLLM(
            model="deepseek-r1:8b"
        )

        self.redis = redis.Redis.from_url(settings.redis_url)
        self.upload_dir = settings.UPLOAD_DIR
        self.chat_repository = ChatRepository(db)

    async def chat_with_websocket(
            self,
            user_id: str,
            chat_params: ChatParamsEntity
    ):
        try:
            prompt = chat_params.prompt

            if chat_params.type == "document":
                context = await self.build_context(
                    chat_params.prompt,
                    user_id,
                    chat_params.directoryId
                )
                if context:
                    prompt = f"Context: {context}\n\nQuestion: {chat_params.prompt}"
                else:
                    yield "No relevant documents found for your query."
                    return

            # Create the chat prompt template
            chat_template = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful AI assistant."),
                ("human", "{prompt}")
            ])

            # Format the prompt
            formatted_prompt = chat_template.format_messages(prompt=prompt)

            # Stream the response from the model
            async for chunk in self.chat_model.astream(formatted_prompt):
                if chunk:
                    yield chunk.content

        except Exception as e:
            logger.error(f"WebSocket chat error: {str(e)}", exc_info=True)
            yield f"Error occurred: {str(e)}"

    async def build_context(self, query: str, user_id: str, directory_id: str) -> str:
        try:
            filters = {
                "user_id": user_id,
                "directory_id": directory_id
            }
            results = self.elasticsearch_store.similarity_search(query,filters=[{"term":{f"metadata.{key}":value for key,value in filters.items()}}])
            if not results:
                return ""

            context_parts = []
            for doc in results:
                source_info = f"From {doc.metadata.get('filename', 'unknown')}"
                if 'page' in doc.metadata:
                    source_info += f" (page {doc.metadata['page']})"

                context_parts.append(f"{source_info}:\n{doc.page_content}\n")

            context = "\n".join(context_parts)

            max_length = 3000
            if len(context) > max_length:
                context = context[:max_length] + "... [truncated]"

            return context

        except Exception as e:
            logger.error(f"Error building context from documents: {str(e)}", exc_info=True)
            return ""

    async def process_text_content(
            self,
            content: str,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str
    ):
        try:
            if not content.strip():
                raise ValueError("内容不能为空")

            text_splitter = CharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )

            texts = text_splitter.split_text(content)
            if not texts:
                raise ValueError("分割后无有效文本")

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

            try:
                self.elasticsearch_store.add_documents(documents)
            except Exception as e:
                logger.warning(f"索引文档失败， {str(e)}")


        except Exception as e:
            logger.error(f"处理文本内容失败: {str(e)}", exc_info=True)
            raise

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
            pdf_reader = PdfReader(BytesIO(content))
            full_text = ""

            # 检查PDF是否有文本内容
            if not pdf_reader.pages:
                raise HTTPException(status_code=400, detail="PDF文件无有效内容")

            for page_num, page in enumerate(pdf_reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"Page {page_num}:\n{page_text}\n\n"
                except Exception as e:
                    logger.warning(f"Page {page_num} text extraction failed: {str(e)}")
                    continue

            if not full_text.strip():
                raise HTTPException(status_code=400, detail="无法从PDF提取文本内容")

            # 处理文本内容
            await self.process_text_content(
                full_text,
                filename,
                user_id,
                doc_id,
                directory_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}", exc_info=True)
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

    async def get_doc_List(self,user_id:str) -> ResultEntity:
        return ResultUtil.success(data=self.chat_repository.get_doc_List(user_id))