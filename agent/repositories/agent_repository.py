from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from chat.models.chat_model import ChatHistory
import logging

logger = logging.getLogger(__name__)


class AgentRepository:
    """Agent数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    def get_chat_history_list(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 10
    ) -> List[ChatHistory]:
        """
        获取用户的聊天历史记录列表
        
        查询字段:
            id, user_id, files, chat_id, prompt, content, model_id, create_time
        
        固定查询条件:
            tenant_id = 'music'
        
        Args:
            user_id: 用户ID
            offset: 偏移量
            limit: 限制条数
            
        Returns:
            聊天历史记录列表
        """
        try:
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
                ChatHistory.tenant_id == 'music'  # 新增：固定租户条件
            ).order_by(
                desc(ChatHistory.create_time)
            ).offset(offset).limit(limit)
            
            # 返回完整对象列表
            results = query.all()
            
            # 将查询结果转换为ChatHistory对象列表（保持一致性）
            chat_history_list = []
            for row in results:
                chat = ChatHistory()
                chat.id = row[0]
                chat.user_id = row[1]
                chat.files = row[2]
                chat.chat_id = row[3]
                chat.prompt = row[4]
                chat.content = row[5]
                chat.model_id = row[6]
                chat.create_time = row[7]
                chat_history_list.append(chat)
            
            return chat_history_list
            
        except Exception as e:
            logger.error(f"查询聊天历史列表失败: user_id={user_id}, error={str(e)}", exc_info=True)
            raise

    def get_chat_history_count(self, user_id: str) -> int:
        """
        获取用户的聊天历史记录总数
        
        固定查询条件:
            tenant_id = 'music'
        
        Args:
            user_id: 用户ID
            
        Returns:
            总记录数
        """
        try:
            count = self.db.query(func.count(ChatHistory.id)).filter(
                ChatHistory.user_id == user_id,
                ChatHistory.tenant_id == 'music'  # 新增：固定租户条件
            ).scalar()
            return count or 0
            
        except Exception as e:
            logger.error(f"查询聊天历史总数失败: user_id={user_id}, error={str(e)}", exc_info=True)
            raise