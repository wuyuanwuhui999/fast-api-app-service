from fastapi import APIRouter, Depends, UploadFile, Header, HTTPException, WebSocket, WebSocketDisconnect, Query
from chat.schemas.chat_schema import ChatParamsEntity, CreateDirectoryShema
from chat.services.chat_service import ChatService
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/service/chat", tags=["chat"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getModelList")
async def get_model_list(
    companyId: str = Query(..., description="企业ID，可选，用于筛选企业下的模型"),
    chat_service: ChatService = Depends()
):
    return await chat_service.get_model_list(companyId)


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    X_User_Id: str = Query(None, alias="X-User-Id"),
    chat_service: ChatService = Depends()
):
    """
    WebSocket聊天接口
    
    用户ID通过URL参数X-User-Id传递（由网关设置）
    其他参数（prompt, chatId, modelId等）通过WebSocket send方法传递
    """
    
    if not X_User_Id:
        await websocket.close(code=4001, reason="Missing user id")
        return
    
    user_id = X_User_Id
    logger.info(f"WebSocket连接建立，用户ID: {user_id}")
    
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                if isinstance(data, str):
                    chat_params_data = json.loads(data)
                else:
                    chat_params_data = data
                
                chat_params = ChatParamsEntity(
                    prompt=chat_params_data.get("prompt", ""),
                    systemPrompt=chat_params_data.get("systemPrompt", None),
                    directoryId=chat_params_data.get("directoryId", "default"),
                    chatId=chat_params_data.get("chatId", ""),
                    token="",
                    modelId=chat_params_data.get("modelId", ""),
                    showThink=chat_params_data.get("showThink", False),
                    type=chat_params_data.get("type", None),
                    language=chat_params_data.get("language", None),
                    tenant_id=chat_params_data.get("tenant_id", None)
                )
                
                async for response in chat_service.chat_with_websocket(user_id, chat_params):
                    await websocket.send_text(response)
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析错误: {str(e)}")
                await websocket.send_text(f"Error: Invalid JSON format - {str(e)}")
                await websocket.send_text("[completed]")
            except Exception as e:
                logger.error(f"处理消息错误: {str(e)}", exc_info=True)
                await websocket.send_text(f"Error: {str(e)}")
                await websocket.send_text("[completed]")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket连接断开，用户ID: {user_id}")
    except Exception as e:
        logger.error(f"WebSocket错误: {str(e)}", exc_info=True)
        try:
            await websocket.close(code=4000, reason=f"Internal error: {str(e)}")
        except:
            pass


@router.post("/uploadDoc")
async def upload_doc(
    file: UploadFile,
    directoryId: str = "public",
    tenantId: str = "personal",
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.upload_doc(file, current_user_id, directoryId, tenantId)


@router.delete("/deleteDoc/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.delete_document(doc_id, current_user_id)


@router.get("/getChatHistory")
async def get_history(
    pageNum: int = 1,
    pageSize: int = 10,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.get_chat_history(current_user_id, pageNum, pageSize)


@router.get("/getDocListByDirId")
async def get_doc_list(
    directoryId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.get_doc_list(current_user_id, directoryId)


@router.get("/getDirectoryList")
async def get_directory_list(
    tenantId: str,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.get_directory_list(current_user_id, tenantId)


@router.post("/createDir")
async def create_directory(
    request: CreateDirectoryShema,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.create_directory(
        current_user_id,
        request.tenantId,
        request.directory
    )