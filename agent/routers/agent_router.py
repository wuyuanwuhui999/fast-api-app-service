# agent/routers/agent_router.py
from fastapi import APIRouter, Depends, Query, Header, HTTPException
from common.utils.result_util import ResultEntity, ResultUtil
from agent.services.agent_service import AgentService

router = APIRouter(prefix="/service/agent", tags=["agent"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getChatHistory", response_model=ResultEntity)
async def get_chat_history(
    pageNum: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user_id: str = Depends(get_user_id_from_header),
    agent_service: AgentService = Depends()
) -> ResultEntity:
    """
    获取当前用户的聊天历史记录
    
    Args:
        pageNum: 页码，从1开始
        pageSize: 每页记录数，最大100
        current_user_id: 当前登录用户ID（由网关透传）
        agent_service: Agent服务实例
        
    Returns:
        分页的聊天历史记录
    """
    return await agent_service.get_chat_history(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )