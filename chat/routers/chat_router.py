# chat/routers/chat_router.py
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, Header, HTTPException, WebSocket, WebSocketDisconnect, Query, Body, Path
from fastapi.responses import StreamingResponse
from chat.schemas.chat_schema import ChatParamsEntity, CreateDirectoryShema, RenameDirectorySchema
from chat.schemas.chat_schema import AddModelSchema, UpdateModelSchema  # 新增导入
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


# ==================== 聊天接口 ====================

@router.post("/chat")
async def chat(
        chat_params: ChatParamsEntity = Body(..., description="聊天参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """
    AI 对话（HTTP 流式）
    与 WebSocket 聊天逻辑一致，流式返回文本
    """
    return StreamingResponse(
        chat_service.chat_with_websocket(current_user_id, chat_params),
        media_type="text/plain;charset=utf-8"
    )


@router.get("/getChatHistoryByChatId")
async def get_chat_history_by_chat_id(
        chatId: str = Query(..., description="会话ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """根据会话ID获取聊天历史"""
    return await chat_service.get_chat_history_by_chat_id(current_user_id, chatId)


# ==================== 文档/目录接口 ====================

@router.get("/getDocList")
async def get_doc_list(
        tenantId: str = Query(..., description="租户ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """获取指定租户下的文档列表"""
    return await chat_service.get_doc_list_by_tenant(current_user_id, tenantId)


@router.put("/renameDir")
async def rename_dir(
        directory_data: RenameDirectorySchema = Body(..., description="重命名目录参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """重命名目录"""
    return await chat_service.rename_directory(current_user_id, directory_data.id, directory_data.directory)


@router.put("/deleteDir/{directoryId}")
async def delete_dir(
        directoryId: str = Path(..., description="目录ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """删除目录"""
    return await chat_service.delete_directory(current_user_id, directoryId)


@router.get("/getModelList")
async def get_model_list(
        companyId: str = Query(..., description="企业ID，可选，用于筛选企业下的模型"),
        keyword: Optional[str] = Query(None, description="搜索关键词，按模型名称模糊搜索"),
        chat_service: ChatService = Depends()
):
    return await chat_service.get_model_list(companyId, keyword)


# ==================== 新增模型管理接口 ====================

@router.post("/addModel")
async def add_model(
        model_data: AddModelSchema = Body(..., description="添加模型请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """
    添加模型
    需要当前用户在企业中为管理员（role > 0）
    """
    return await chat_service.add_model(model_data, current_user_id)


@router.put("/updateModel")
async def update_model(
        model_data: UpdateModelSchema = Body(..., description="更新模型请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """
    更新模型
    需要当前用户在企业中为管理员（role > 0）
    """
    return await chat_service.update_model(model_data, current_user_id)


@router.delete("/deleteModel/{modelId}")
async def delete_model(
        modelId: str,
        companyId: str = Query(..., description="企业ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """
    删除模型（软删除）
    需要当前用户在企业中为管理员（role > 0）
    """
    return await chat_service.delete_model(modelId, companyId, current_user_id)


# ==================== 原有的其他接口 ====================

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

                # 提取 docIds 数组（前端字段名为 docIds）
                doc_ids = chat_params_data.get("docIds", [])
                if doc_ids and not isinstance(doc_ids, list):
                    doc_ids = [doc_ids] if isinstance(doc_ids, str) else []

                chat_params = ChatParamsEntity(
                    prompt=chat_params_data.get("prompt", ""),
                    systemPrompt=chat_params_data.get("systemPrompt", None),
                    docIds=doc_ids,
                    chatId=chat_params_data.get("chatId", ""),
                    modelId=chat_params_data.get("modelId", ""),
                    showThink=chat_params_data.get("showThink", False),
                    type=chat_params_data.get("type", None),
                    language=chat_params_data.get("language", None),
                    companyId=chat_params_data.get("companyId", None),
                    tenantId=chat_params_data.get("tenantId", None)
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


@router.post("/uploadDoc/{tenantId}/{directoryId}")
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
        pageNum: int = Query(1, ge=1, description="页码"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量"),
        tenantId: Optional[str] = Query(None, description="租户ID，可选，不传则查询所有租户"),
        current_user_id: str = Depends(get_user_id_from_header),
        chat_service: ChatService = Depends()
):
    """
    获取聊天历史记录

    Args:
        pageNum: 页码，从1开始
        pageSize: 每页数量，最大100
        tenantId: 租户ID（可选），不传则查询该用户所有租户的聊天记录
        current_user_id: 当前登录用户ID
    """
    return await chat_service.get_chat_history(current_user_id, pageNum, pageSize, tenantId)


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