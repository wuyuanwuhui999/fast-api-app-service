from fastapi import APIRouter, Depends, UploadFile, Header, HTTPException, WebSocket, WebSocketDisconnect
from chat.schemas.chat_schema import ChatParamsEntity, CreateDirectoryShema
from chat.services.chat_service import ChatService

router = APIRouter(prefix="/service/chat", tags=["chat"])


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getModelList")
async def get_model_list(chat_service: ChatService = Depends()):
    return await chat_service.get_model_list()


@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    chat_service: ChatService = Depends()
):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            chat_params = ChatParamsEntity(**data)
            # WebSocket场景下，token应该从消息中获取并验证
            # 这里由gateway已经验证过，直接从token解析用户ID
            from common.utils.jwt_util import verify_token
            import json
            payload = verify_token(chat_params.token)
            if not payload:
                await websocket.send_text("认证失败")
                await websocket.close()
                return
            sub = payload.get("sub")
            if isinstance(sub, str):
                user_info = json.loads(sub)
                user_id = user_info.get("id")
            else:
                user_id = sub.get("id") if sub else None
            
            async for response in chat_service.chat_with_websocket(user_id, chat_params):
                await websocket.send_text(response)
    except WebSocketDisconnect:
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


@router.get("/getDocList")
async def get_doc_list(
    tenantId: str = None,
    current_user_id: str = Depends(get_user_id_from_header),
    chat_service: ChatService = Depends()
):
    return await chat_service.get_doc_list(current_user_id, tenantId)


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