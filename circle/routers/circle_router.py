# circle/routers/circle_router.py
from typing import Optional

from fastapi import APIRouter, Depends, Query, Header, HTTPException, WebSocket, WebSocketDisconnect, Body

from common.utils.result_util import ResultEntity
from circle.schemas.circle_schema import InsertCircleSchema
from circle.services.circle_service import CircleService
from circle.websocket_manager import manager

router = APIRouter(
    prefix="/service/circle",
    tags=["circle"],
    responses={404: {"description": "Not found"}}
)


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


# ==================== 朋友圈接口 ====================

@router.get("/getCircleListByType", response_model=ResultEntity)
async def get_circle_list_by_type(
        pageSize: int = Query(..., description="每页数量"),
        pageNum: int = Query(..., description="页码，从1开始"),
        type: str = Query(..., description="类型（MUSIC/MOVIE）"),
        circle_service: CircleService = Depends()
) -> ResultEntity:
    """获取朋友圈列表（按类型分页）"""
    return await circle_service.get_circle_list_by_type(
        page_num=pageNum,
        page_size=pageSize,
        circle_type=type
    )


@router.get("/getCircleArticleCount", response_model=ResultEntity)
async def get_circle_article_count(
        id: int = Query(..., description="朋友圈文章ID"),
        circle_service: CircleService = Depends()
) -> ResultEntity:
    """获取文章的评论数量、浏览数量、收藏数量"""
    return await circle_service.get_circle_article_count(circle_id=id)


@router.post("/insertCircle", response_model=ResultEntity)
async def insert_circle(
        circle_data: InsertCircleSchema = Body(..., description="朋友圈请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        circle_service: CircleService = Depends()
) -> ResultEntity:
    """保存图片和文字（发布朋友圈）"""
    return await circle_service.insert_circle(circle_data, current_user_id)


@router.get("/getCircleByLastUpdateTime", response_model=ResultEntity)
async def get_circle_by_last_update_time(
        lastUpdateTime: str = Query(..., description="上次更新时间"),
        type: str = Query(..., description="类型（MUSIC/MOVIE）"),
        circle_service: CircleService = Depends()
) -> ResultEntity:
    """获取最近更新的朋友圈数量"""
    return await circle_service.get_circle_by_last_update_time(
        last_update_time=lastUpdateTime,
        circle_type=type
    )


# ==================== WebSocket ====================

@router.websocket("/ws")
async def websocket_circle(websocket: WebSocket):
    """
    朋友圈 WebSocket 广播接口

    与 Spring 中 /service/circle/ws 的 MyWebSocketHandler 对齐：
    - 连接建立后加入连接池
    - 收到客户端消息时广播给所有连接
    - 发布新朋友圈时由 service 广播"有一条新消息"
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 将收到的消息广播给所有连接的客户端
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
