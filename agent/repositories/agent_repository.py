# agent/repositories/agent_repository.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import re

from agent.schemas.agent_schema import ChatHistorySchema, ChatModelSchema

logger = logging.getLogger(__name__)


class AgentRepository:
    """Agent数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    async def get_model_by_id(self, model_id: str) -> Optional[ChatModelSchema]:
        """根据模型ID获取模型配置"""
        try:
            from chat.models.chat_model import ChatModel
            
            model = self.db.query(ChatModel).filter(
                ChatModel.id == model_id,
                ChatModel.disabled == 0
            ).first()
            
            if model:
                return ChatModelSchema(
                    id=model.id,
                    type=model.type,
                    api_key=model.api_key,
                    model_name=model.model_name,
                    base_url=model.base_url,
                    disabled=model.disabled,
                    create_time=model.create_time,
                    update_time=model.update_time
                )
            return None
        except Exception as e:
            logger.error(f"获取模型配置失败: {str(e)}")
            return None

    async def save_chat_history(self, chat_data: ChatHistorySchema) -> bool:
        """保存聊天记录到数据库"""
        try:
            from chat.models.chat_model import ChatHistory
            
            db_chat = ChatHistory(
                user_id=chat_data.user_id,
                tenant_id=chat_data.tenant_id or "music",
                model_id=chat_data.model_id,
                files=chat_data.files,
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
            self.db.rollback()
            logger.error(f"保存聊天记录失败: {str(e)}", exc_info=True)
            return False

    async def get_chat_history(
            self,
            user_id: str,
            offset: int = 0,
            limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户的聊天历史记录"""
        try:
            from chat.models.chat_model import ChatHistory
            
            query = self.db.query(
                ChatHistory.id,
                ChatHistory.user_id,
                ChatHistory.files,
                ChatHistory.chat_id,
                ChatHistory.prompt,
                ChatHistory.content,
                ChatHistory.model_id,
                ChatHistory.create_time
            ).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.tenant_id == "music"
            ).order_by(
                desc(ChatHistory.create_time)
            ).offset(offset).limit(limit)
            
            results = query.all()
            
            return [
                {
                    "id": row[0],
                    "user_id": row[1],
                    "files": row[2],
                    "chat_id": row[3],
                    "prompt": row[4],
                    "content": row[5],
                    "model_id": row[6],
                    "create_time": row[7].strftime("%Y-%m-%d %H:%M:%S") if row[7] else None
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"查询聊天历史失败: {str(e)}")
            return []

    async def get_chat_history_count(self, user_id: str) -> int:
        """获取用户的聊天历史记录总数"""
        try:
            from chat.models.chat_model import ChatHistory
            
            count = self.db.query(func.count(ChatHistory.id)).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.tenant_id == "music"
            ).scalar()
            return count or 0
        except Exception as e:
            logger.error(f"查询聊天历史总数失败: {str(e)}")
            return 0

    async def execute_music_query(
            self,
            sql_condition: str,
            keyword: str,
            limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        执行音乐查询
        
        Args:
            sql_condition: SQL WHERE条件
            keyword: 搜索关键词
            limit: 最大返回数量
        """
        try:
            from sqlalchemy import text
            
            like_keyword = f"%{keyword}%"
            
            # 如果没有提供有效的 SQL 条件，使用默认查询
            if not sql_condition or sql_condition.strip() == "":
                full_sql = """
                    SELECT 
                        id, song_name, author_name, album_name, cover, play_url, label
                    FROM music 
                    WHERE song_name LIKE :keyword 
                       OR author_name LIKE :keyword 
                       OR label LIKE :keyword
                    LIMIT :limit
                """
                result = self.db.execute(
                    text(full_sql), 
                    {"keyword": like_keyword, "limit": limit}
                )
            else:
                # 处理 SQL 条件：将 %%s%% 替换为实际的 LIKE 语句
                # 例如: "author_name LIKE '%%s%%'" -> "author_name LIKE :keyword"
                processed_condition = sql_condition
                
                # 替换 %%s%% 为 :keyword
                processed_condition = re.sub(r"%%s%%", ":keyword", processed_condition)
                processed_condition = re.sub(r"%s", ":keyword", processed_condition)
                
                # 构建完整 SQL
                full_sql = f"""
                    SELECT 
                        id, song_name, author_name, album_name, cover, play_url, label
                    FROM music 
                    WHERE {processed_condition}
                    LIMIT :limit
                """
                
                logger.info(f"[execute_music_query] SQL: {full_sql}")
                logger.info(f"[execute_music_query] keyword: {like_keyword}")
                
                result = self.db.execute(
                    text(full_sql), 
                    {"keyword": like_keyword, "limit": limit}
                )
            
            rows = result.fetchall()
            return [
                {
                    "id": row[0],
                    "song_name": row[1],
                    "author_name": row[2],
                    "album_name": row[3],
                    "cover": row[4],
                    "play_url": row[5],
                    "label": row[6]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"音乐查询失败: {str(e)}", exc_info=True)
            return []

    async def get_user_like_status(self, user_id: str, music_id: int) -> int:
        """获取用户对音乐的点赞状态"""
        try:
            from sqlalchemy import text
            
            result = self.db.execute(
                text("SELECT COUNT(*) FROM music_like WHERE user_id = :user_id AND music_id = :music_id"),
                {"user_id": user_id, "music_id": music_id}
            )
            count = result.scalar()
            return 1 if count and count > 0 else 0
        except Exception as e:
            logger.error(f"查询点赞状态失败: {str(e)}")
            return 0

    async def get_user_favorite_status(self, user_id: str, music_id: int) -> int:
        """获取用户对音乐的收藏状态"""
        try:
            from sqlalchemy import text
            
            result = self.db.execute(
                text("""
                    SELECT COUNT(*) FROM music_favorite_list fl
                    JOIN music_favorite_directory fd ON fl.favorite_id = fd.id
                    WHERE fd.user_id = :user_id AND fl.music_id = :music_id
                """),
                {"user_id": user_id, "music_id": music_id}
            )
            count = result.scalar()
            return 1 if count and count > 0 else 0
        except Exception as e:
            logger.error(f"查询收藏状态失败: {str(e)}")
            return 0