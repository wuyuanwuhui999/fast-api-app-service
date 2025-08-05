from typing import Optional
from langchain import (
    EmbeddingModel,
    ElasticsearchEmbeddingStore,
    TextSegment,
    Embedding,
    EmbeddingSearchRequest,
    Filter,
    IsEqualTo
)


class PromptUtil:
    @staticmethod
    async def build_context(
            embedding_model: EmbeddingModel,
            elasticsearch_store: ElasticsearchEmbeddingStore,
            query: str,
            user_id: str,
            directory_id: Optional[str] = None
    ) -> str:
        query_embedding = await embedding_model.embed(query)
        user_filter = IsEqualTo("metadata.user_id", user_id)

        if directory_id:
            directory_filter = IsEqualTo("metadata.directory_id", directory_id)
            search_filter = Filter.and_(directory_filter, user_filter)
        else:
            search_filter = user_filter

        search_request = EmbeddingSearchRequest(
            query_embedding=query_embedding,
            filter=search_filter
        )

        results = await elasticsearch_store.search(search_request)
        if not results.matches:
            return ""

        context = ["以下是一些相关的文档摘录，可能有助于回答您的问题:\n\n"]
        for match in results.matches:
            segment = match.embedded()
            filename = segment.metadata.get("filename", "未知文件")
            page = segment.metadata.get("page", "未知页码")

            context.append(
                f"文档来源: {filename}, 第{page}页\n"
                f"内容: {segment.text}\n\n"
            )

        return "".join(context)

    @staticmethod
    def get_file_extension(filename: str) -> str:
        if not filename:
            return ""

        dot_index = filename.rfind(".")
        if dot_index == -1 or dot_index == len(filename) - 1:
            return ""

        return filename[dot_index + 1:]