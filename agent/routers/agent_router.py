# agent/routers/agent_router.py
from fastapi import APIRouter, Depends, Query, Header, HTTPException, WebSocket, WebSocketDisconnect
import json
import logging

from common.utils.result_util import ResultEntity, ResultUtil
from agent.services.agent_service import AgentService
from agent.schemas.agent_schema import AgentParamsEntity

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service/agent", tags=["agent"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    X_User_Id: str = Query(None, alias="X-User-Id"),
    agent_service: AgentService = Depends()
):
    """
    WebSocket聊天接口
    """
    if not X_User_Id:
        await websocket.close(code=4001, reason="Missing user id")
        return
    
    user_id = X_User_Id
    logger.info(f"[AgentWebSocket] WebSocket连接建立，用户ID: {user_id}")
    
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                chat_params_data = json.loads(data)
                
                chat_params = AgentParamsEntity(
                    prompt=chat_params_data.get("prompt", ""),
                    directoryId=chat_params_data.get("directoryId", "default"),
                    chatId=chat_params_data.get("chatId", ""),
                    modelId=chat_params_data.get("modelId", ""),
                    showThink=chat_params_data.get("showThink", False),
                    tenant_id=chat_params_data.get("tenant_id", "music")
                )
                
                if not chat_params.prompt:
                    await websocket.send_text("Error: prompt不能为空")
                    await websocket.send_text("[completed]")
                    continue
                
                if not chat_params.chatId:
                    await websocket.send_text("Error: chatId不能为空")
                    await websocket.send_text("[completed]")
                    continue
                
                if not chat_params.modelId:
                    await websocket.send_text("Error: modelId不能为空")
                    await websocket.send_text("[completed]")
                    continue
                
                async for response in agent_service.chat_with_websocket(user_id, chat_params):
                    await websocket.send_text(response)
                    
            except json.JSONDecodeError as e:
                logger.error(f"[AgentWebSocket] JSON解析错误: {str(e)}")
                await websocket.send_text(f"Error: Invalid JSON format - {str(e)}")
                await websocket.send_text("[completed]")
            except Exception as e:
                logger.error(f"[AgentWebSocket] 处理消息错误: {str(e)}", exc_info=True)
                await websocket.send_text(f"Error: {str(e)}")
                await websocket.send_text("[completed]")
                
    except WebSocketDisconnect:
        logger.info(f"[AgentWebSocket] WebSocket连接断开，用户ID: {user_id}")
    except Exception as e:
        logger.error(f"[AgentWebSocket] WebSocket错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"Internal error: {str(e)}")
        except:
            pass


@router.get("/getChatHistory", response_model=ResultEntity)
async def get_chat_history(
    pageNum: int = Query(1, ge=1, description="页码"),
    pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
    current_user_id: str = Depends(get_user_id_from_header),
    agent_service: AgentService = Depends()
) -> ResultEntity:
    """获取当前用户的聊天历史记录"""
    result = await agent_service.get_chat_history(
        user_id=current_user_id,
        page_num=pageNum,
        page_size=pageSize
    )
    return ResultEntity(**result)