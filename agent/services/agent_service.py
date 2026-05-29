import asyncio
import uuid
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator, Any, List, Dict

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from langchain_community.chat_models import ChatOpenAI
from langchain_ollama import OllamaLLM
from langchain.prompts.chat import ChatPromptTemplate

from common.config.common_database import get_db
from common.config.common_config import get_settings
from common.utils.result_util import ResultUtil
from agent.repositories.agent_repository import AgentRepository
from agent.schemas.agent_schema import AgentParamsEntity, ChatHistorySchema, ChatModelSchema, MusicSchema

import redis

logger = logging.getLogger(__name__)
settings = get_settings()


class AgentService:
    """Agent服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.agent_repository = AgentRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)
        self.db = db

    def get_music_system_prompt(self, user_id: str) -> str:
        """获取音乐查询系统提示词（包含当前用户ID）"""
        return f"""
# Role
你是一个专业的音乐数据库查询助手。你的核心任务是分析用户的自然语言输入，提取音乐相关的查询意图，并基于给定的数据库表结构生成对应的 JSON 格式指令和 SQL WHERE 条件。

## 重要上下文信息：
1. **当前用户**: {user_id}

# Database Schema Context
请严格基于以下表结构生成查询条件：
1. music (主表):
- 字段: id, song_name, author_name, album_name, language, publish_date, is_hot, label, cover, local_play_url, lyrics
- 注意: music表没有user_id字段！
2. music_favorite_list (用户收藏表):
- 关联字段: music_id, user_id, favorite_id
3. music_like (用户点赞表):
- 关联字段: music_id, user_id

# Query Logic & Constraints
1. **关联查询**: 查询音乐时，必须通过 LEFT JOIN 关联 music_favorite_list 和 music_like 表，以判断当前用户 (userId={user_id}) 的收藏和点赞状态。
2. **状态字段**: 关联后需生成 is_favorite (1:已收藏, 0:未收藏) 和 is_like (1:已点赞, 0:未点赞) 的逻辑。
3. **占位符**: SQL 条件中的参数占位符统一使用 %s。
4. **输出限制**: 仅输出标准的 JSON 格式，严禁包含任何 Markdown 标记（如 ```json）或额外的解释性文字。

# Output Format
请严格返回以下 JSON 结构：
{{
    "is_music_related": true/false,
    "explanation": "简短说明用户的意图或与音乐无关的原因",
    "search_type": "song_name | author_name | album_name | label | hot | none",
    "search_keyword": "提取的纯关键词（不含SQL通配符）",
    "sql_condition": "生成的SQL WHERE条件字符串",
    "join_tables": ["music_favorite_list", "music_like"]
}}

# SQL Generation Rules
1. 模糊查询使用 LIKE '%%s%%'，精确查询使用 = %s。
2. 默认查询逻辑为 SELECT * FROM music LEFT JOIN ... WHERE [sql_condition]。
3. 如果用户未指定具体条件（如"推荐热门歌曲"），sql_condition 可为 "1=1"。
4. 涉及用户状态的过滤（如"我收藏的歌"），请在 sql_condition 中显式使用 user_id = %s。

# Examples

User Input: "我想听周杰伦的歌"
Output:
{{
    "is_music_related": true,
    "explanation": "用户想查询歌手为周杰伦的歌曲",
    "search_type": "author_name",
    "search_keyword": "周杰伦",
    "sql_condition": "author_name LIKE '%%s%%'",
    "join_tables": ["music_favorite_list", "music_like"]
}}

User Input: "帮我找一下我收藏的关于夏天的歌"
Output:
{{
    "is_music_related": true,
    "explanation": "用户查询当前用户收藏列表中歌名或标签包含'夏天'的歌曲",
    "search_type": "song_name",
    "search_keyword": "夏天",
    "sql_condition": "(song_name LIKE '%%s%%' OR label LIKE '%%s%%') AND music_favorite_list.user_id = %s AND music_favorite_list.music_id IS NOT NULL",
    "join_tables": ["music_favorite_list", "music_like"]
}}

User Input: "今天天气怎么样"
Output:
{{
    "is_music_related": false,
    "explanation": "用户询问天气，与音乐查询无关"
}}
"""

    async def chat_with_websocket(
            self,
            user_id: str,
            chat_params: AgentParamsEntity
    ) -> AsyncGenerator[str, None]:
        """
        WebSocket聊天处理
        
        Args:
            user_id: 用户ID（由网关验证后传递）
            chat_params: 聊天参数
        """
        logger.info(f"[AgentService] ========== 开始处理聊天请求 ==========")
        logger.info(f"[AgentService] user_id={user_id}")
        logger.info(f"[AgentService] chatId={chat_params.chatId}")
        logger.info(f"[AgentService] modelId={chat_params.modelId}")
        logger.info(f"[AgentService] tenant_id={chat_params.tenant_id}")
        logger.info(f"[AgentService] prompt={chat_params.prompt[:50] if chat_params.prompt else 'None'}...")

        # 创建聊天记录实体
        chat_entity = ChatHistorySchema(
            user_id=user_id,
            tenant_id="music",  # 固定租户ID为music
            model_id=chat_params.modelId,
            files=None,
            chat_id=chat_params.chatId,
            prompt=chat_params.prompt,
            system_prompt=None,
            think_content=None,
            response_content=None,
            content=""
        )

        try:
            # 1. 从数据库获取模型配置
            model_config = await self.agent_repository.get_model_by_id(chat_params.modelId)
            if not model_config:
                logger.error(f"[AgentService] 未找到模型配置: {chat_params.modelId}")
                yield f"Error: 未找到模型配置 {chat_params.modelId}"
                yield "[completed]"
                return

            logger.info(f"[AgentService] 获取到模型配置: id={model_config.id}, type={model_config.type}, model_name={model_config.model_name}")

            # 2. 使用AI提取音乐意图并生成SQL
            intent_result = await self._extract_music_intent(
                chat_params.prompt,
                model_config,
                chat_params.showThink,
                user_id
            )

            if not intent_result.get("is_music_related", False):
                yield "抱歉，我只能回答与音乐相关的问题。请尝试询问关于歌曲、歌手、专辑或音乐标签的问题。"
                yield "[completed]"
                return

            # 3. 执行音乐查询
            music_list = await self._execute_music_query(
                intent_result.get("sql_condition", ""),
                intent_result.get("search_keyword", ""),
                user_id
            )

            # 4. 格式化返回结果
            if music_list:
                response_text = self._format_music_response(music_list, intent_result.get("explanation", ""))
            else:
                response_text = "抱歉，没有找到符合您要求的音乐。请尝试其他关键词或描述。"

            # 5. 流式返回结果
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)

            # 发送完成标识
            yield "[completed]"

            # 6. 保存聊天记录
            chat_entity.content = response_text
            chat_entity.response_content = response_text
            chat_entity.create_time = datetime.now()

            asyncio.create_task(self.save_chat_history_async(chat_entity))

        except Exception as e:
            logger.error(f"[AgentService] WebSocket chat error: {str(e)}", exc_info=True)
            yield f"Error occurred: {str(e)}"
            yield "[completed]"

    async def _extract_music_intent(
            self,
            prompt: str,
            model_config: ChatModelSchema,
            show_think: bool,
            user_id: str
    ) -> Dict[str, Any]:
        """
        使用AI提取音乐意图并生成查询SQL条件
        
        Returns:
            {
                "is_music_related": bool,
                "explanation": str,
                "search_type": str,
                "search_keyword": str,
                "sql_condition": str
            }
        """
        try:
            chat_model = await self._create_chat_model(model_config, show_think)
            
            messages = [
                ("system", self.get_music_system_prompt(user_id)),
                ("human", f"用户输入: {prompt}")
            ]
            
            response = await chat_model.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            logger.info(f"[AgentService] 意图提取结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"[AgentService] 意图提取失败: {str(e)}")
            return await self._fallback_intent_extraction(prompt)

    async def _fallback_intent_extraction(self, prompt: str) -> Dict[str, Any]:
        """降级的意图提取方法"""
        music_keywords = ["歌", "音乐", "歌曲", "歌手", "专辑", "唱", "听", "播放"]
        is_music = any(keyword in prompt for keyword in music_keywords)
        
        if not is_music:
            return {"is_music_related": False, "explanation": "未检测到音乐相关关键词"}
        
        import re
        quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
        if quoted:
            keyword = quoted[0]
        else:
            words = prompt.replace("推荐", "").replace("搜索", "").replace("找", "").replace("听", "")
            keyword = words.strip()[:50]
        
        return {
            "is_music_related": True,
            "explanation": f"搜索音乐关键词: {keyword}",
            "search_type": "song_name",
            "search_keyword": keyword,
            "sql_condition": "(song_name LIKE '%%s%%' OR author_name LIKE '%%s%%' OR label LIKE '%%s%%')"
        }

    async def _execute_music_query(
            self,
            sql_condition: str,
            keyword: str,
            user_id: str
    ) -> List[Dict[str, Any]]:
        """执行音乐查询并获取点赞/收藏状态"""
        try:
            music_list = await self.agent_repository.execute_music_query(
                sql_condition, 
                keyword, 
                limit=20
            )
            
            if not music_list:
                return []
            
            result = []
            for music in music_list:
                music_dict = dict(music)
                music_dict['is_like'] = await self.agent_repository.get_user_like_status(user_id, music['id'])
                music_dict['is_favorite'] = await self.agent_repository.get_user_favorite_status(user_id, music['id'])
                result.append(music_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"[AgentService] 音乐查询失败: {str(e)}", exc_info=True)
            return []

    def _format_music_response(self, music_list: List[Dict[str, Any]], explanation: str = "") -> str:
        """格式化音乐查询结果为用户友好的文本"""
        if not music_list:
            return "抱歉，没有找到符合您要求的音乐。"
        
        response_lines = [explanation if explanation else "为您找到以下音乐：", ""]
        
        for i, music in enumerate(music_list[:10], 1):
            song_name = music.get('song_name', '未知歌曲')
            author_name = music.get('author_name', '未知歌手')
            album_name = music.get('album_name', '')
            label = music.get('label', '')
            
            like_status = "❤️ 已点赞" if music.get('is_like') else "🤍 未点赞"
            fav_status = "⭐ 已收藏" if music.get('is_favorite') else "☆ 未收藏"
            
            line = f"{i}. 《{song_name}》 - {author_name}"
            if album_name:
                line += f" (专辑: {album_name})"
            if label:
                line += f" [标签: {label}]"
            line += f"\n   {like_status} | {fav_status}"
            
            response_lines.append(line)
        
        if len(music_list) > 10:
            response_lines.append(f"\n... 共找到{len(music_list)}首歌曲，仅显示前10首")
        
        return "\n".join(response_lines)

    async def _create_chat_model(self, model_config: ChatModelSchema, show_think: bool) -> Any:
        """根据模型配置创建对应的聊天模型实例"""
        try:
            if model_config.type == "ollama":
                logger.info(f"[AgentService] 创建Ollama模型: {model_config.model_name}")
                return OllamaLLM(
                    model=model_config.model_name,
                    base_url=model_config.base_url or "http://localhost:11434",
                    model_kwargs={"options": {"think": show_think}}
                )
            elif model_config.type in ["deepseek", "tongyi"]:
                base_url = model_config.base_url
                if model_config.type == "deepseek":
                    base_url = base_url or "https://api.deepseek.com/v1"
                elif model_config.type == "tongyi":
                    base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
                
                logger.info(f"[AgentService] 创建在线模型: {model_config.type}, base_url={base_url}")
                return ChatOpenAI(
                    model=model_config.model_name,
                    api_key=model_config.api_key,
                    base_url=base_url,
                    streaming=True,
                    temperature=0.7
                )
            else:
                logger.error(f"[AgentService] 不支持的模型类型: {model_config.type}")
                return None
        except Exception as e:
            logger.error(f"[AgentService] 创建聊天模型失败: {str(e)}")
            return None

    async def save_chat_history_async(self, chat_entity: ChatHistorySchema):
        """异步保存聊天记录"""
        try:
            success = await self.agent_repository.save_chat_history(chat_entity)
            if success:
                logger.info(f"[AgentService] 聊天记录保存成功: user_id={chat_entity.user_id}, chat_id={chat_entity.chat_id}")
            else:
                logger.error("保存聊天记录返回False")
        except Exception as e:
            logger.error(f"后台保存聊天记录失败: {str(e)}", exc_info=True)

    async def get_chat_history(
            self,
            user_id: str,
            page_num: int = 1,
            page_size: int = 10
    ) -> Dict[str, Any]:
        """获取用户的聊天历史记录（分页）"""
        try:
            offset = (page_num - 1) * page_size
            chat_history_list = await self.agent_repository.get_chat_history(
                user_id=user_id,
                offset=offset,
                limit=page_size
            )
            total = await self.agent_repository.get_chat_history_count(user_id)
            
            return ResultUtil.success(data=chat_history_list, total=total).model_dump()
        except Exception as e:
            logger.error(f"获取聊天历史失败: {str(e)}")
            return ResultUtil.fail(data=None, msg=f"获取聊天历史失败: {str(e)}").model_dump()