import asyncio
import uuid
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, AsyncGenerator, Any, List, Dict

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from common.config.common_database import get_db, SessionLocal
from common.utils.result_util import ResultUtil
from agent.repositories.agent_repository import AgentRepository
from agent.schemas.agent_schema import AgentParamsEntity, ChatHistorySchema, ChatModelSchema, MusicSchema
from agent.services.llm_logger import (
    LlmTraceCallback,
    log_llm_request,
    log_llm_response,
    log_model_instance,
    log_tool_plan,
    log_tool_sql,
    log_tool_user_status,
)
import os
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# ==================== 会话记忆（MongoDB） ====================
# 会话上下文（对话记忆）存 MongoDB：库 chat / 集合 chat_memory，
# 通过 update_time 字段 + TTL 索引实现 180 天过期；MySQL 的 chat_history 仍保留双写。
MONGODB_HOST = os.getenv("MONGODB_HOST", "localhost")
MONGODB_PORT = int(os.getenv("MONGODB_PORT", "27017"))
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "chat")
AGENT_MEMORY_COLLECTION = "chat_memory"
AGENT_MEMORY_TTL_SECONDS = 180 * 24 * 3600
AGENT_MEMORY_MAX_MESSAGES = 20

# 全局 MongoDB 客户端（懒连接：首个操作时才真正建立连接）
_mongo_client = MongoClient(MONGODB_HOST, MONGODB_PORT, serverSelectionTimeoutMS=3000)
_agent_memory_collection = _mongo_client[MONGODB_DATABASE][AGENT_MEMORY_COLLECTION]


class AgentService:
    """Agent服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.agent_repository = AgentRepository(db)
        self.mongo_agent_memory = _agent_memory_collection
        # 幂等创建 TTL 索引（180 天过期，已存在则跳过）
        try:
            self.mongo_agent_memory.create_index("update_time", expireAfterSeconds=AGENT_MEMORY_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"[AgentService] 创建 MongoDB TTL 索引失败: {e}")
        self.db = db

    @staticmethod
    def get_history_key(user_id: str, chat_id: str) -> str:
        """会话记忆在 MongoDB 中的文档 _id"""
        return f"agent_history:{user_id}:{chat_id}"

    def _get_agent_history_from_mongo(self, key: str) -> Optional[str]:
        """从 MongoDB 读取会话上下文（返回 JSON 字符串，不存在则返回 None）"""
        try:
            doc = self.mongo_agent_memory.find_one({"_id": key})
            if doc:
                return doc.get("messages")
        except Exception as e:
            logger.error(f"[AgentService] 从 MongoDB 读取会话失败: {e}")
        return None

    def _save_agent_history_to_mongo(self, key: str, user_id: str, chat_id: str, messages_json: str):
        """保存会话上下文到 MongoDB（upsert，TTL 由 update_time 索引控制）"""
        try:
            self.mongo_agent_memory.update_one(
                {"_id": key},
                {"$set": {
                    "user_id": user_id,
                    "chat_id": chat_id,
                    "messages": messages_json,
                    "update_time": datetime.utcnow(),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"[AgentService] 保存会话到 MongoDB 失败: {e}")

    def load_agent_history(self, user_id: str, chat_id: str) -> List[tuple]:
        """读取历史会话上下文，返回 [(role, content), ...]（无历史或解析失败返回空列表）"""
        key = self.get_history_key(user_id, chat_id)
        raw = self._get_agent_history_from_mongo(key)
        if not raw:
            return []
        try:
            loaded = json.loads(raw)
            history = [(item[0], item[1]) for item in loaded if isinstance(item, (list, tuple)) and len(item) == 2]
            logger.info(f"[AgentService] 已从 MongoDB 加载历史会话: key={key}, 消息数={len(history)}")
            return history
        except Exception as e:
            logger.warning(f"[AgentService] 解析 MongoDB 会话上下文失败: {e}")
            return []

    def append_and_save_agent_history(
            self,
            user_id: str,
            chat_id: str,
            history: List[tuple],
            prompt: str,
            reply: str
    ) -> None:
        """把本轮问答追加到会话上下文并写入 MongoDB（最多保留最近 N 条）"""
        try:
            updated = list(history) + [("human", prompt), ("ai", reply)]
            if len(updated) > AGENT_MEMORY_MAX_MESSAGES:
                updated = updated[-AGENT_MEMORY_MAX_MESSAGES:]
            key = self.get_history_key(user_id, chat_id)
            self._save_agent_history_to_mongo(
                key, user_id, chat_id, json.dumps(updated, ensure_ascii=False)
            )
            logger.info(f"[AgentService] 会话已保存到 MongoDB: key={key}, 消息数={len(updated)}")
        except Exception as e:
            logger.error(f"[AgentService] 保存会话上下文失败: {e}")

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
            3. **参数占位符**: SQL 条件中的参数占位符统一使用 :keyword（冒号加参数名），不要使用 %s 或 %%s%%。
            4. **输出限制**: 仅输出标准的 JSON 格式，严禁包含任何 Markdown 标记（如 ```json）或额外的解释性文字。

            # Output Format
            请严格返回以下 JSON 结构：
            {{
                "is_music_related": true/false,
                "explanation": "简短说明用户的意图或与音乐无关的原因",
                "search_type": "song_name | author_name | album_name | label | hot | none",
                "search_keyword": "提取的纯关键词（不含SQL通配符）",
                "sql_condition": "生成的SQL WHERE条件字符串（使用 :keyword 作为参数占位符）",
                "join_tables": ["music_favorite_list", "music_like"]
            }}

            # SQL Generation Rules
            1. 模糊查询使用 LIKE :keyword，精确查询使用 = :keyword。
            2. 默认查询逻辑为 SELECT * FROM music LEFT JOIN ... WHERE [sql_condition]。
            3. 如果用户未指定具体条件（如"推荐热门歌曲"），sql_condition 可为 "1=1"。
            4. 涉及用户状态的过滤（如"我收藏的歌"），请在 sql_condition 中显式使用 user_id = :user_id（注意使用 :user_id 占位符）。

            # Examples

            User Input: "我想听周杰伦的歌"
            Output:
            {{
                "is_music_related": true,
                "explanation": "用户想查询歌手为周杰伦的歌曲",
                "search_type": "author_name",
                "search_keyword": "周杰伦",
                "sql_condition": "author_name LIKE :keyword",
                "join_tables": ["music_favorite_list", "music_like"]
            }}

            User Input: "帮我找一下我收藏的关于夏天的歌"
            Output:
            {{
                "is_music_related": true,
                "explanation": "用户查询当前用户收藏列表中歌名或标签包含'夏天'的歌曲",
                "search_type": "song_name",
                "search_keyword": "夏天",
                "sql_condition": "(song_name LIKE :keyword OR label LIKE :keyword) AND music_favorite_list.user_id = :user_id AND music_favorite_list.music_id IS NOT NULL",
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
        logger.info(
            f"[AgentService] WS请求参数: user_id={user_id}, chatId={chat_params.chatId}, "
            f"modelId={chat_params.modelId}, "
            f"tenant_id={chat_params.tenant_id}, showThink={chat_params.showThink}"
        )
        logger.info(f"[AgentService] 用户prompt(全文)={chat_params.prompt}")

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

            # 2. 读取历史会话上下文（MongoDB），用于多轮对话
            history = self.load_agent_history(user_id, chat_params.chatId)

            # 3. 使用AI提取音乐意图并生成SQL
            intent_result = await self._extract_music_intent(
                chat_params.prompt,
                model_config,
                chat_params.showThink,
                user_id,
                history=history
            )

            if not intent_result.get("is_music_related", False):
                reply = "抱歉，我只能回答与音乐相关的问题。请尝试询问关于歌曲、歌手、专辑或音乐标签的问题。"
                self.append_and_save_agent_history(
                    user_id, chat_params.chatId, history, chat_params.prompt, reply
                )
                yield reply
                yield "[completed]"
                return

            # 4. 执行音乐查询
            music_list = await self._execute_music_query(
                intent_result.get("sql_condition", ""),
                intent_result.get("search_keyword", ""),
                user_id
            )

            # 5. 格式化返回结果
            if music_list:
                response_text = self._format_music_response(music_list, intent_result.get("explanation", ""))
                # 5.1 末尾追加 <music> 标签：把 SQL 查询结果以 JSON 列表形式给前端，用于生成音乐列表
                #     （查询不到数据时 music_list 为空，不输出该标签）
                response_text += self._format_music_tag(music_list)
            else:
                response_text = "抱歉，没有找到符合您要求的音乐。请尝试其他关键词或描述。"

            # 6. 流式返回结果
            chunk_size = 50
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)

            # 7. 会话上下文写入 MongoDB（MySQL chat_history 仍保留双写）
            self.append_and_save_agent_history(
                user_id, chat_params.chatId, history, chat_params.prompt, response_text
            )

            # 发送完成标识
            yield "[completed]"

            # 8. 保存聊天记录（MySQL）
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
            user_id: str,
            history: Optional[List[tuple]] = None
    ) -> Dict[str, Any]:
        """
        使用AI提取音乐意图并生成查询SQL条件

        Args:
            history: 历史会话上下文 [(role, content), ...]（来自 MongoDB，用于多轮对话）

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
                ("system", self.get_music_system_prompt(user_id))
            ]
            if history:
                messages.extend(history)
            messages.append(("human", f"用户输入: {prompt}"))

            # ---- 观测：打印发给大模型的参数 + 完整提示词 ----
            log_llm_request(
                stage="_extract_music_intent（音乐意图提取）",
                request_params={
                    "user_id": user_id,
                    "prompt(用户输入)": prompt,
                    "showThink": show_think,
                    "modelId": getattr(model_config, "id", None),
                    "messages条数": len(messages),
                    "system_prompt字符数": len(messages[0][1]),
                },
                model_config=model_config,
                show_think=show_think,
                messages=messages,
            )

            started = time.perf_counter()
            response = await chat_model.ainvoke(
                messages,
                config={"callbacks": [LlmTraceCallback(stage="_extract_music_intent")]},
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            response_text = response.content if hasattr(response, 'content') else str(response)

            # ---- 观测：打印模型原始返回 ----
            log_llm_response("_extract_music_intent（音乐意图提取）", response, elapsed_ms)

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text.strip())
            logger.info(f"[AgentService] 意图提取结果: {result}")
            # ---- 观测：LLM 生成的「工具计划」（意图 + 待执行 SQL 条件） ----
            log_tool_plan(result)
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
            # ---- 观测：工具调用（数据库查询），带上 LLM 生成的 SQL 条件 ----
            log_tool_sql(
                sql=(f"SELECT id, song_name, author_name, album_name, cover, play_url, label "
                     f"FROM music WHERE {sql_condition or '<空条件，走默认 LIKE 查询>'} LIMIT 20"),
                params={"keyword": f"%{keyword}%", "limit": 20},
            )

            music_list = await self.agent_repository.execute_music_query(
                sql_condition, 
                keyword, 
                limit=20
            )

            logger.info(f"[AgentLLM] 工具调用(数据库查询) 实际返回 {len(music_list)} 行")

            if not music_list:
                return []

            result = []
            status_calls = 0
            for i, music in enumerate(music_list):
                music_dict = dict(music)
                music_dict['is_like'] = await self.agent_repository.get_user_like_status(user_id, music['id'])
                music_dict['is_favorite'] = await self.agent_repository.get_user_favorite_status(user_id, music['id'])
                result.append(music_dict)
                status_calls += 2
                # 只打印前 5 条明细，避免刷屏
                if i < 5:
                    log_tool_user_status(music.get('id'), music_dict['is_like'], music_dict['is_favorite'])

            logger.info(
                f"[AgentLLM] 工具调用汇总: 查询命中 {len(result)} 首音乐, "
                f"用户状态查询 {status_calls} 次 (user_id={user_id})"
            )
            return result
            
        except Exception as e:
            logger.error(f"[AgentService] 音乐查询失败: {str(e)}", exc_info=True)
            return []

    def _format_music_tag(self, music_list: List[Dict[str, Any]]) -> str:
        """把 SQL 查询结果以 JSON 列表放进 <music></music> 标签，供前端解析生成音乐列表。

        - 无数据（空列表）时返回空串 —— 调用方拼接到响应末尾，因此「查不到数据就不输出 <music> 标签」
        - 字段用 camelCase，与音乐模块接口（getMusicList 等）返回的音乐对象保持一致，前端可复用同一个类型
        """
        if not music_list:
            return ""

        items = [
            {
                "id": music.get("id"),
                "songName": music.get("song_name"),
                "authorName": music.get("author_name"),
                "albumName": music.get("album_name"),
                "cover": music.get("cover"),
                "playUrl": music.get("play_url"),
                "label": music.get("label"),
                "isLike": music.get("is_like", 0),
                "isFavorite": music.get("is_favorite", 0),
            }
            for music in music_list
        ]

        try:
            tag = "<music>" + json.dumps(items, ensure_ascii=False) + "</music>"
            logger.info(f"[AgentService] 输出 <music> 标签: {len(items)} 首音乐")
            return tag
        except Exception as e:
            logger.error(f"[AgentService] 生成 <music> 标签失败: {str(e)}")
            return ""

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
                model = ChatOllama(
                    model=model_config.model_name,
                    base_url=model_config.base_url,
                    reasoning=show_think
                )
                log_model_instance(model, stage="_create_chat_model")
                return model
            elif model_config.type == "online":
                base_url = model_config.base_url
                
                logger.info(f"[AgentService] 创建在线模型: {model_config.type}, base_url={base_url}")
                model = ChatOpenAI(
                    model=model_config.model_name,
                    api_key=model_config.api_key,
                    base_url=base_url,
                    streaming=True,
                    temperature=0.7
                )
                log_model_instance(model, stage="_create_chat_model")
                return model
            else:
                logger.error(f"[AgentService] 不支持的模型类型: {model_config.type}")
                return None
        except Exception as e:
            logger.error(f"[AgentService] 创建聊天模型失败: {str(e)}")
            return None

    async def save_chat_history_async(self, chat_entity: ChatHistorySchema):
        """异步保存聊天记录（MySQL 双写）。

        注意：必须用独立的 SessionLocal，不能用请求作用域的 self.agent_repository ——
        WebSocket 关闭后请求 Session 会被回收，后台任务再写就会失败丢记录。
        """
        db = SessionLocal()
        try:
            success = await AgentRepository(db).save_chat_history(chat_entity)
            if success:
                logger.info(f"[AgentService] 聊天记录保存成功(MySQL): user_id={chat_entity.user_id}, chat_id={chat_entity.chat_id}")
            else:
                logger.error("保存聊天记录返回False")
        except Exception as e:
            logger.error(f"后台保存聊天记录失败: {str(e)}", exc_info=True)
        finally:
            db.close()

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