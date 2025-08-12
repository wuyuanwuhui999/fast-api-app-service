import asyncio
import uuid
import logging
from datetime import timedelta

from fastapi import UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
import os
from langchain.memory import BaseMemory
from chat.repositories.chat_repository import ChatRepository
from chat.schemas.chat_schema import ChatDocSchema, ChatParamsEntity, ChatSchema
from chat.utils.chat_util import PromptUtil
from common.config.common_config import get_settings
from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
import redis
from pypdf import PdfReader
from langchain_elasticsearch import ElasticsearchStore
from langchain.prompts.chat import ChatPromptTemplate
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from io import BytesIO

logger = logging.getLogger(__name__)
settings = get_settings()


class ChatService:
    def __init__(
            self,
            db: Session = Depends(get_db)
    ):
        self.elasticsearch_store = ElasticsearchStore(
            es_url="http://localhost:9200",
            index_name="chat_vector_index",
            embedding=OllamaEmbeddings(model="nomic-embed-text:latest")
        )

        # 初始化模型映射字典
        self.model_mapping = {
            "deepseek-r1:8b": lambda show_think: OllamaLLM(
                model="deepseek-r1:8b",
                model_kwargs={"options": {"think": show_think}}
            ),
            "qwen3:8b": lambda show_think: OllamaLLM(
                model="qwen3:8b",
                model_kwargs={"options": {"think": show_think}}
            )
        }

        self.redis = redis.Redis.from_url(settings.redis_url)
        self.upload_dir = settings.UPLOAD_DIR
        self.chat_repository = ChatRepository(db)

    async def chat_with_websocket(
            self,
            user_id: str,
            chat_params: ChatParamsEntity
    ):
        chat_entity = ChatSchema(
            user_id=user_id,
            chat_id=chat_params.chatId,
            prompt=chat_params.prompt,
            model_name=chat_params.modelName,
            content="",
            think_content=None,
            response_content=None
        )

        response_collector = []

        try:
            # 从Redis获取或初始化会话记忆
            chat_history_key = f"chat_history:{user_id}:{chat_params.chatId}"
            chat_history = self.redis.get(chat_history_key)

            # 初始化聊天模板
            messages = [
                ("system", "你叫小吴同学，是一个无所不能的AI助手，上知天文下知地理，请用小吴同学的身份回答问题。")
            ]

            # 如果有历史会话，添加到消息中
            if chat_history:
                try:
                    messages.extend(eval(chat_history.decode('utf-8')))
                except Exception as e:
                    logger.warning(f"Failed to parse chat history from Redis: {str(e)}")

            # 添加当前用户消息
            messages.append(("human", chat_params.prompt))

            # 根据 modelName 和 showThink 获取对应的模型实例
            model_factory = self.model_mapping.get(chat_params.modelName)
            if not model_factory:
                yield f"Error: 不支持的大模型 {chat_params.modelName}"
                yield "[completed]"
                return

            # 根据 showThink 参数创建模型实例
            chat_model = model_factory(chat_params.showThink)

            chat_template = ChatPromptTemplate.from_messages(messages)

            # 构建上下文（如果是文档类型）
            prompt = chat_params.prompt
            if chat_params.type == "document":
                context = await self.build_context(
                    chat_params.prompt,
                    user_id,
                    chat_params.directoryId,
                    tenant_id=chat_params.tenant_id
                )
                if context:
                    prompt = f"请参考内容: {context}\n\n回答问题: {chat_params.prompt}"
                else:
                    yield "对不起，没有查询到相关文档！"
                    yield "[completed]"
                    return

            formatted_prompt = chat_template.format_messages(prompt=prompt)

            # 流式返回模型响应
            full_response = ""
            async for chunk in chat_model.astream(
                    formatted_prompt,
                    config={"configurable": {"session_id": chat_params.chatId}},
            ):
                chunk_str = str(chunk)
                response_collector.append(chunk_str)
                full_response += chunk_str
                yield chunk_str

            # 保存当前会话到Redis
            try:
                # 只保留最近的10轮对话避免内存过大
                updated_messages = messages.copy()
                updated_messages.append(("ai", full_response))
                if len(updated_messages) > 20:  # 10轮对话(每轮user+AI)
                    updated_messages = updated_messages[-20:]

                # 设置过期时间为180天
                await self.redis.setex(
                    chat_history_key,
                    timedelta(days=180),
                    str(updated_messages)
                )
            except Exception as e:
                logger.error(f"Failed to save chat history to Redis: {str(e)}")

            # 保存对话记录
            chat_entity.content = full_response
            chat_entity.set_content(chat_entity.content)

            yield "[completed]"
            # 异步保存记录
            asyncio.create_task(self.save_chat_history_async(chat_entity, full_response))
        except Exception as e:
            logger.error(f"WebSocket chat error: {str(e)}", exc_info=True)
            yield f"Error occurred: {str(e)}"
            yield "[completed]"

    async def save_chat_history_async(self, chat_entity: ChatSchema, content: str):
        """异步保存聊天记录的辅助方法"""
        try:
            if not self.chat_repository:
                logger.error("chat_repository 未初始化")
                return

            chat_entity.content = content
            chat_entity.set_content(content)

            # 确保返回的是协程对象
            result = await self.chat_repository.save_chat_history(chat_entity)
            if not result:
                logger.error("保存聊天记录返回False")

        except Exception as e:
            logger.error(f"后台保存聊天记录失败: {str(e)}", exc_info=True)

    async def build_context(self, query: str, user_id: str, directory_id: str, tenant_id: str = None) -> str:
        try:
            filters = {
                "user_id": user_id,
                "directory_id": directory_id,
                "tenant_id": tenant_id
            }

            valid_filters = {k: v for k, v in filters.items() if v is not None and v != ""}

            filter_query = [{"term": {f"metadata.{key}": value}} for key, value in
                            valid_filters.items()] if valid_filters else []

            results = self.elasticsearch_store.similarity_search(
                query,
                filters=filter_query if filter_query else None
            )

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

    def process_text_content(
            self,
            content: str,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str,
            tenant_id: str = None
    ):
        try:
            if not content.strip():
                raise ValueError("内容不能为空")

            text_splitter = RecursiveCharacterTextSplitter(
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
                        "tenant_id": tenant_id,
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

    def process_pdf(
            self,
            content: bytes,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str,
            tenant_id: str
    ):
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
            self.process_text_content(
                full_text,
                filename,
                user_id,
                doc_id,
                directory_id,
                tenant_id
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"PDF处理失败: {str(e)}")

    def process_txt(
            self,
            content: bytes,
            filename: str,
            user_id: str,
            doc_id: str,
            directory_id: str,
            tenant_id: str = None
    ):
        """Process TXT file and store embeddings"""
        try:
            text_content = content.decode('utf-8')
            self.process_text_content(
                text_content,
                filename,
                user_id,
                doc_id,
                directory_id,
                tenant_id
            )
        except Exception as e:
            logger.error(f"TXT processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"TXT处理失败: {str(e)}")

    async def get_model_list(self) -> ResultEntity:
        return ResultUtil.success(data=self.chat_repository.get_model_list())

    async def delete_document(self, doc_id: str, user_id: str, directory_id: str):
        doc = await self.chat_repository.get_doc_by_id(doc_id, user_id, directory_id)
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在或无权删除")

        file_path = os.path.join(
            self.upload_dir,
            f"{doc.id}{'.' + doc.ext if doc.ext else ''}"
        )
        if os.path.exists(file_path):
            os.remove(file_path)

        await self.chat_repository.delete_doc(doc_id, user_id, directory_id)

        return ResultUtil.success(msg="文档删除成功")

    #
    async def get_chat_history(self, user_id: str, page: int = 1, size: int = 10) -> ResultEntity:
        start = (page - 1) * size
        chat_history_list = self.chat_repository.get_chat_history(user_id, start, size)
        total = self.chat_repository.get_chat_history_total(user_id)
        return ResultUtil.success(data=chat_history_list, total=total)

    async def upload_doc(self, file: UploadFile, user_id: str, directory_id: str,tenant_id:str) -> ResultEntity:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        ext = PromptUtil.get_file_extension(file.filename)
        if ext.lower() not in ["pdf", "txt"]:
            raise HTTPException(status_code=400, detail="只能上传pdf和txt的文档")

        doc_id = str(uuid.uuid4()).replace("-", "")

        try:
            content = await file.read()

            if ext.lower() == "pdf":
                self.process_pdf(content, file.filename, user_id, doc_id, directory_id,tenant_id)
            else:
                self.process_txt(content, file.filename, user_id, doc_id, directory_id,tenant_id)

            file_path = os.path.join(self.upload_dir, file.filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

            doc = ChatDocSchema(
                id=doc_id,
                user_id=user_id,
                name=file.filename,
                ext=ext,
                directory_id=directory_id,
                tenant_id=tenant_id
            )
            await self.chat_repository.save_doc(doc)

            return ResultUtil.success(msg="文件上传成功")

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    async def get_doc_List(self,user_id:str,tenant_id:str = None) -> ResultEntity:
        return ResultUtil.success(data=self.chat_repository.get_doc_List(user_id,tenant_id))