import asyncio
import uuid
import logging
from datetime import timedelta
from typing import List, Any

from fastapi import UploadFile, HTTPException, Depends
from langchain_community.chat_models import ChatOpenAI
from sqlalchemy.orm import Session
import os
from chat.repositories.chat_repository import ChatRepository
from chat.schemas.chat_schema import ChatDocSchema, ChatParamsEntity, ChatSchema, ChatModelSchema
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
from chat.schemas.chat_schema import DirectorySchema

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

        self.redis = redis.Redis.from_url(settings.redis_url)
        self.upload_dir = settings.UPLOAD_DIR
        self.chat_repository = ChatRepository(db)
        self.db = db

    async def chat_with_websocket(
            self,
            user_id: str,
            chat_params: ChatParamsEntity
    ):
        chat_entity = ChatSchema(
            user_id=user_id,
            chat_id=chat_params.chatId,
            prompt=chat_params.prompt,
            system_prompt = chat_params.systemPrompt,
            model_name=chat_params.modelId,  # 使用modelId
            content="",
            think_content=None,
            response_content=None
        )

        response_collector = []

        try:
            # 从数据库获取模型配置
            model_config = self.chat_repository.get_model_by_id(chat_params.modelId)
            if not model_config:
                yield f"Error: 未找到模型配置 {chat_params.modelId}"
                yield "[completed]"
                return

            # 根据模型类型创建对应的聊天模型
            chat_model = await self._create_chat_model(model_config, chat_params.showThink)
            if not chat_model:
                yield f"Error: 不支持的模型类型 {model_config.type}"
                yield "[completed]"
                return

            # 从Redis获取或初始化会话记忆
            chat_history_key = f"chat_history:{user_id}:{chat_params.chatId}"
            chat_history = self.redis.get(chat_history_key)

            # 初始化聊天模板
            messages = [
                ("system", chat_params.systemPrompt if chat_params.systemPrompt is None or chat_params.systemPrompt == '' else "你叫小吴同学，是一个无所不能的AI助手，上知天文下知地理，请用小吴同学的身份回答问题。")
            ]

            # 如果有历史会话，添加到消息中
            if chat_history:
                try:
                    messages.extend(eval(chat_history.decode('utf-8')))
                except Exception as e:
                    logger.warning(f"Failed to parse chat history from Redis: {str(e)}")

            # 添加当前用户消息
            messages.append(("human", chat_params.prompt))

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

            # 根据模型类型调用不同的流式接口
            if model_config.type == "ollama":
                async for chunk in chat_model.astream(
                        formatted_prompt,
                        config={"configurable": {"session_id": chat_params.chatId}},
                ):
                    chunk_str = str(chunk)
                    response_collector.append(chunk_str)
                    full_response += chunk_str
                    yield chunk_str
            else:
                # 在线大模型的流式处理
                async for chunk in self._stream_online_model(chat_model, formatted_prompt):
                    chunk_str = chunk
                    response_collector.append(chunk_str)
                    full_response += chunk_str
                    yield chunk_str

            # 保存当前会话到Redis
            try:
                updated_messages = messages.copy()
                updated_messages.append(("ai", full_response))
                if len(updated_messages) > 20:
                    updated_messages = updated_messages[-20:]

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

    async def _create_chat_model(self, model_config: ChatModelSchema, show_think: bool) -> Any:
        """根据模型配置创建对应的聊天模型实例"""
        try:
            if model_config.type == "ollama":
                return OllamaLLM(
                    model=model_config.model_name,
                    base_url=model_config.base_url or "http://localhost:11434",
                    model_kwargs={"options": {"think": show_think}}
                )

            elif model_config.type in ["deepseek", "tongyi"]:
                # 配置基础URL
                base_url = model_config.base_url
                if model_config.type == "deepseek":
                    base_url = base_url or "https://api.deepseek.com/v1"
                elif model_config.type == "tongyi":
                    base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"

                return ChatOpenAI(
                    model=model_config.model_name,
                    api_key=model_config.api_key,
                    base_url=base_url,
                    streaming=True,
                    temperature=0.7
                )

            else:
                logger.error(f"不支持的模型类型: {model_config.type}")
                return None

        except Exception as e:
            logger.error(f"创建聊天模型失败: {str(e)}")
            return None

    async def _stream_online_model(self, chat_model, formatted_prompt):
        """处理在线大模型的流式响应"""
        try:
            # 对于在线大模型，使用aiter的方式处理流式响应
            async for chunk in chat_model.astream(formatted_prompt):
                if hasattr(chunk, 'content'):
                    yield chunk.content
                else:
                    yield str(chunk)
        except Exception as e:
            logger.error(f"在线大模型流式处理失败: {str(e)}")
            yield f"模型响应错误: {str(e)}"

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

    async def delete_document(self, doc_id: str, user_id: str):
        doc = await self.chat_repository.get_doc_by_id(doc_id, user_id)
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
            self.chat_repository.save_doc(doc)
            return ResultUtil.success(msg="文件上传成功")

        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

    async def get_doc_List(self,user_id:str,tenant_id:str = None) -> ResultEntity:
        return ResultUtil.success(data=self.chat_repository.get_doc_List(user_id,tenant_id))

    # 在ChatService类中添加以下方法
    async def get_directory_list(self, user_id: str, tenant_id: str) -> ResultEntity:
        """
        获取租户下的文件夹列表
        需要先验证用户是否在该租户内且用户未被禁用
        """
        try:
            # 首先验证用户是否存在且未被禁用
            from user.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.db)

            user = user_repo.get_user_by_id(user_id)
            if not user:
                return ResultUtil.fail(msg="用户不存在",data=None)

            if user.disabled == 1:  # 检查用户是否被禁用
                return ResultUtil.fail(msg="用户已被禁用，无法访问",data=None)
            elif tenant_id != user_id:
                # 验证用户是否在租户内
                from tenant.repositories.tenants_repository import TenantsRepository
                tenants_repo = TenantsRepository(self.db)

                tenant_user = await tenants_repo.get_tenant_user_role(tenant_id,user_id)
                if not tenant_user:
                    return ResultUtil.fail(msg="用户不在该租户内或无访问权限",data=None)

            # 查询文件夹列表
            directory_list = await self._get_directory_list_by_tenant(tenant_id, user_id)

            return ResultUtil.success(data=directory_list)

        except Exception as e:
            logger.error(f"获取文件夹列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取文件夹列表失败: {str(e)}",data=None)

    async def _get_directory_list_by_tenant(self, tenant_id: str, user_id: str) -> List[DirectorySchema]:
        """
        根据租户ID和用户ID查询文件夹列表
        """
        try:
            from chat.models.chat_model import ChatDocDirectory
            from chat.schemas.chat_schema import DirectorySchema

            # 查询当前租户下的文件夹，包括公共目录和用户自己的目录
            directories = self.db.query(ChatDocDirectory).filter(
                (ChatDocDirectory.tenant_id == tenant_id) &
                (ChatDocDirectory.user_id == user_id)
            ).order_by(
                ChatDocDirectory.create_time.desc()
            ).all()

            return [
                DirectorySchema(
                    id=dir.id,
                    user_id=dir.user_id,
                    directory=dir.directory,
                    tenant_id=dir.tenant_id,
                    create_time=dir.create_time.strftime("%Y-%m-%d %H:%M:%S") if dir.create_time else None,
                    update_time=dir.update_time.strftime("%Y-%m-%d %H:%M:%S") if dir.update_time else None
                ) for dir in directories
            ]

        except Exception as e:
            logger.error(f"查询文件夹列表失败: {str(e)}", exc_info=True)
            return []

    # 在ChatService类中修改_check_directory_exists方法
    async def _check_directory_exists(self, tenant_id: str, user_id: str, directory_name: str) -> bool:
        """
        检查文件夹是否已存在（当前租户和当前用户下）
        """
        try:
            # 检查用户个人文件夹是否已存在
            user_dir_exists = await self.chat_repository.check_directory_exists(tenant_id, user_id, directory_name)

            # 检查公共文件夹是否已存在
            public_dir_exists = await self.chat_repository.check_public_directory_exists(tenant_id, directory_name)

            return user_dir_exists or public_dir_exists

        except Exception as e:
            logger.error(f"检查文件夹是否存在失败: {str(e)}")
            return False

    # 修改create_directory方法，添加更详细的错误提示
    async def create_directory(self, user_id: str, tenant_id: str, directory_name: str) -> ResultEntity:
        """
        创建文件夹
        需要验证用户是否启用且在指定租户内，并检查文件夹是否已存在
        """
        try:
            # 验证文件夹名称
            directory_name = directory_name.strip()
            if not directory_name:
                return ResultUtil.fail(msg="文件夹名称不能为空")

            if len(directory_name) > 255:
                return ResultUtil.fail(msg="文件夹名称长度不能超过255个字符")

            # 首先验证用户是否存在且未被禁用
            from user.repositories.user_repository import UserRepository
            user_repo = UserRepository(self.db)

            user = user_repo.get_user_by_id(user_id)
            if not user:
                return ResultUtil.fail(msg="用户不存在")

            if user.disabled == 1:  # 检查用户是否被禁用
                return ResultUtil.fail(msg="用户已被禁用，无法创建文件夹")

            # 验证用户是否在租户内
            from tenant.repositories.tenants_repository import TenantsRepository
            tenants_repo = TenantsRepository(self.db)

            tenant_user = await tenants_repo.get_tenant_user_role(tenant_id,user_id)
            if not tenant_user:
                return ResultUtil.fail(msg="用户不在该租户内或无权限创建文件夹",data=None)

            # 检查文件夹是否已存在（当前租户下，包括用户个人文件夹和公共文件夹）
            if await self._check_directory_exists(tenant_id, user_id, directory_name):
                return ResultUtil.fail(msg="文件夹名称已存在，请使用其他名称")

            # 创建文件夹并获取完整的文件夹对象
            directory_obj = await self._create_directory_in_db(tenant_id, user_id, directory_name)

            # 通用的返回数据处理
            if hasattr(directory_obj, 'model_dump'):
                data = directory_obj.model_dump()
            elif hasattr(directory_obj, 'dict'):
                data = directory_obj.dict()
            else:
                data = directory_obj

            return ResultUtil.success(data=data, msg="文件夹创建成功")

        except Exception as e:
            logger.error(f"创建文件夹失败: {str(e)}", exc_info=True)

    async def _create_directory_in_db(self, tenant_id: str, user_id: str, directory_name: str) -> ResultEntity:
        """
        在数据库中创建文件夹
        """
        try:
            directory = await self.chat_repository.create_directory(tenant_id, user_id, directory_name)
            return ResultUtil.success(data=directory.model_dump())
        except Exception as e:
            logger.error(f"数据库创建文件夹失败: {str(e)}")
            raise HTTPException(status_code=500, detail="创建文件夹失败")