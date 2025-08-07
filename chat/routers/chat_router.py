from fastapi import APIRouter, Depends, UploadFile, WebSocket
from chat.schemas.chat_schema import ChatParamsEntity
from chat.services.chat_service import ChatService
# from chat.dependencies import get_chat_service
from common.dependencies.auth_dependency import get_current_user
from common.schemas.user_schema import UserInDB

router = APIRouter(prefix="/service/ai", tags=["chat"])


@router.get("/getModelList")
async def get_model_list(chat_service: ChatService = Depends()):
    return await chat_service.get_model_list()

#
# @router.websocket("/ws/{user_id}")
# async def websocket_chat(
#         websocket: WebSocket,
#         user_id: str,
#         chat_service: ChatService = Depends(get_chat_service)
# ):
#     await websocket.accept()
#     while True:
#         data = await websocket.receive_json()
#         chat_params = ChatParamsEntity(**data)
#
#         async for response in chat_service.chat_with_websocket(user_id, chat_params):
#             await websocket.send_text(response)
#
#
@router.post("/uploadDoc")
async def upload_document(
        file: UploadFile,
        directory_id: str = "public",
        current_user: UserInDB = Depends(get_current_user),
        chat_service: ChatService = Depends(get_current_user)
):
    return await chat_service.upload_doc(file, current_user.id, directory_id)
#
#
@router.delete("/deleteDoc/{doc_id}")
async def delete_document(
        doc_id: str,
        directory_id: str,
        current_user: UserInDB = Depends(get_current_user),
        chat_service: ChatService = Depends()
):
    return await chat_service.delete_document(doc_id, current_user.id, directory_id)


@router.get("/getChatHistory")
async def get_history(
        pageNum: int = 1,
        pageSize: int = 10,
        current_user: UserInDB = Depends(get_current_user),
        chat_service: ChatService = Depends(get_current_user)
):
    return await chat_service.get_chat_history(current_user.id, pageNum, pageSize)
