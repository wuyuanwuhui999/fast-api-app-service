from fastapi import APIRouter, Depends, UploadFile, WebSocket
from chat.schemas.chat_schema import ChatParamsEntity
from chat.services.chat_service import ChatService
from common.dependencies.auth_dependency import get_current_user
from common.schemas.user_schema import UserSchema

router = APIRouter(prefix="/service/ai", tags=["chat"])


@router.get("/getModelList")
async def get_model_list(chat_service: ChatService = Depends()):
    return await chat_service.get_model_list()

#
@router.websocket("/ws/chat")
async def websocket_chat(
        websocket: WebSocket,
        chat_service: ChatService = Depends()
):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        chat_params = ChatParamsEntity(**data)
        user_data = await get_current_user(chat_params.token)
        async for response in chat_service.chat_with_websocket(user_data.id, chat_params):
            await websocket.send_text(response)


@router.post("/uploadDoc")
async def upload_doc(
        file: UploadFile,
        directoryId: str = "public",
        tenantId: str = "personal",
        current_user: UserSchema = Depends(get_current_user),
        chat_service: ChatService = Depends()
):
    return await chat_service.upload_doc(file, current_user.id, directoryId,tenantId)
#
#
@router.delete("/deleteDoc/{doc_id}")
async def delete_document(
        doc_id: str,
        directory_id: str,
        current_user: UserSchema = Depends(get_current_user),
        chat_service: ChatService = Depends()
):
    return await chat_service.delete_document(doc_id, current_user.id, directory_id)


@router.get("/getChatHistory")
async def get_history(
        pageNum: int = 1,
        pageSize: int = 10,
        current_user: UserSchema = Depends(get_current_user),
        chat_service: ChatService = Depends()
):
    return await chat_service.get_chat_history(current_user.id, pageNum, pageSize)


@router.get("/getDocList")
async def get_doc_List(
        tenant_id: str = None,
        current_user: UserSchema = Depends(get_current_user),
        chat_service: ChatService = Depends()
):
    return await chat_service.get_doc_List(current_user.id,tenant_id)