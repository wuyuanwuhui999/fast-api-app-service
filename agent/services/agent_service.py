# agent/services/agent_service.py
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from agent.repositories.agent_repository import AgentRepository
import logging

logger = logging.getLogger(__name__)


class AgentService:
    """Agent服务业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.agent_repository = AgentRepository(db)

    async def get_chat_history(
        self,
        user_id: str,
        page_num: int = 1,
        page_size: int = 10
    ) -> ResultEntity:
        """
        获取用户的聊天历史记录（分页）
        
        Args:
            user_id: 用户ID
            page_num: 页码，从1开始
            page_size: 每页记录数
            
        Returns:
            分页的聊天历史记录
        """
        try:
            # 计算偏移量
            offset = (page_num - 1) * page_size
            
            # 查询聊天历史列表
            chat_history_list = self.agent_repository.get_chat_history_list(
                user_id=user_id,
                offset=offset,
                limit=page_size
            )
            
            # 查询总记录数
            total = self.agent_repository.get_chat_history_count(user_id)
            
            # 转换数据格式
            data_list = []
            for record in chat_history_list:
                data_list.append({
                    "id": record.id,
                    "user_id": record.user_id,
                    "files": record.files,
                    "chat_id": record.chat_id,
                    "prompt": record.prompt,
                    "content": record.content,
                    "model_id": record.model_id,
                    "create_time": record.create_time.strftime("%Y-%m-%d %H:%M:%S") if record.create_time else None
                })
            
            return ResultUtil.success(
                data=data_list,
                total=total,
                msg="查询成功"
            )
            
        except Exception as e:
            logger.error(f"获取聊天历史失败: user_id={user_id}, error={str(e)}", exc_info=True)
            return ResultUtil.fail(
                data=None,
                msg=f"获取聊天历史失败: {str(e)}"
            )