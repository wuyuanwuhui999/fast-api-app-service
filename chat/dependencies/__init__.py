from fastapi import Depends
from chat.config import settings
from chat.services import ChatService
# from langchain import (
#     OllamaEmbeddingModel,
#     OllamaStreamingChatModel,
#     ElasticsearchEmbeddingStore,
#     RestClient
# )

# def get_embedding_model():
#     return OllamaEmbeddingModel(
#         base_url=settings.OLLAMA_BASE_URL,
#         model_name=settings.EMBEDDING_MODEL,
#         timeout=settings.EMBEDDING_TIMEOUT
#     )
#
# def get_elasticsearch_store():
#     client = RestClient.create(settings.ELASTICSEARCH_URL)
#     return ElasticsearchEmbeddingStore(
#         rest_client=client,
#         index_name=settings.ELASTICSEARCH_INDEX
#     )
#
# def get_qwen_assistant():
#     return OllamaStreamingChatModel(
#         base_url=settings.OLLAMA_BASE_URL,
#         model_name=settings.QWEN_MODEL_NAME,
#         temperature=settings.TEMPERATURE
#     )
#
# def get_deepseek_assistant():
#     return OllamaStreamingChatModel(
#         base_url=settings.OLLAMA_BASE_URL,
#         model_name=settings.DEEPSEEK_MODEL_NAME,
#         temperature=settings.TEMPERATURE
#     )
#
# def get_chat_service(
#     embedding_model: OllamaEmbeddingModel = Depends(get_embedding_model),
#     elasticsearch_store: ElasticsearchEmbeddingStore = Depends(get_elasticsearch_store),
#     qwen_assistant: OllamaStreamingChatModel = Depends(get_qwen_assistant),
#     deepseek_assistant: OllamaStreamingChatModel = Depends(get_deepseek_assistant)
# ) -> ChatService:
#     return ChatService(
#         embedding_model=embedding_model,
#         elasticsearch_store=elasticsearch_store,
#         qwen_assistant=qwen_assistant,
#         deepseek_assistant=deepseek_assistant
#     )