from fastapi import APIRouter, Depends, UploadFile, WebSocket
from chat.schemas import ChatParamsEntity
from chat.services import ChatService
from chat.dependencies import get_chat_service

router = APIRouter(prefix="/service/ai", tags=["chat"])


@router.get("/getModelList")
async def get_model_list(chat_service: ChatService = Depends(get_chat_service)):
    return await chat_service.get_model_list()


@router.websocket("/ws/{user_id}")
async def websocket_chat(
        websocket: WebSocket,
        user_id: str,
        chat_service: ChatService = Depends(get_chat_service)
):
    await websocket.accept()
    while True:
        data = await websocket.receive_json()
        chat_params = ChatParamsEntity(**data)

        async for response in chat_service.chat_with_websocket(user_id, chat_params):
            await websocket.send_text(response)


@router.post("/documents")
async def upload_document(
        file: UploadFile,
        user_id: str,
        directory_id: str = "public",
        chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.upload_doc(file, user_id, directory_id)


@router.delete("/documents/{doc_id}")
async def delete_document(
        doc_id: str,
        user_id: str,
        directory_id: str,
        chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.delete_doc(doc_id, user_id, directory_id)


@router.get("/history")
async def get_history(
        user_id: str,
        page: int = 1,
        size: int = 10,
        chat_service: ChatService = Depends(get_chat_service)
):
    return await chat_service.get_chat_history(user_id, page, size)
