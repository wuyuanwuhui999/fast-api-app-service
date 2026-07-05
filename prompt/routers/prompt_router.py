# prompt/routers/prompt_router.py
from fastapi import APIRouter, Depends, Query, Body, Header, HTTPException, Path
from typing import Optional
from common.utils.result_util import ResultEntity
from prompt.services.prompt_service import PromptService
from prompt.schemas.prompt_schema import UpdatePromptSchema, InsertPromptSchema

router = APIRouter(
    prefix="/service/prompt",
    tags=["prompt"],
    responses={404: {"description": "Not found"}},
)


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


@router.get("/getPrompt", response_model=ResultEntity)
async def get_prompt(
        tenantId: str = Query(..., description="租户ID"),
        promptId: Optional[str] = Query(None, description="提示词ID（可选），传入时根据ID精确查询单条记录"),
        current_user_id: str = Depends(get_user_id_from_header),
        prompt_service: PromptService = Depends()
):
    """
    查询提示词记录

    使用场景：
    1. 当 id 为空时：根据 tenantId 查询租户默认提示词，不存在则自动创建
    2. 当 id 不为空时：根据 id + tenantId 精确查询单条提示词（同时校验用户权限）
    """
    return await prompt_service.get_prompt(tenantId, current_user_id, promptId)


@router.get("/getPromptList", response_model=ResultEntity)
async def get_prompt_list(
        tenantId: str = Query(..., description="租户ID"),
        keyword: Optional[str] = Query(None, description="搜索关键词（对提示词内容进行模糊匹配），为空则查询全部"),
        pageNum: int = Query(1, ge=1, description="页码，从1开始"),
        pageSize: int = Query(10, ge=1, le=100, description="每页数量，最大100"),
        current_user_id: str = Depends(get_user_id_from_header),
        prompt_service: PromptService = Depends()
):
    """
    分页获取当前用户在指定租户下的所有提示词列表
    支持按关键词模糊搜索提示词内容
    """
    return await prompt_service.get_prompt_list(
        tenant_id=tenantId,
        current_user_id=current_user_id,
        keyword=keyword,
        page_num=pageNum,
        page_size=pageSize
    )


@router.post("/insertPrompt", response_model=ResultEntity)
async def insert_prompt(
        prompt_data: InsertPromptSchema = Body(..., description="插入提示词请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        prompt_service: PromptService = Depends()
):
    """插入新的提示词"""
    return await prompt_service.insert_prompt(prompt_data, current_user_id)


@router.delete("/deletePrompt/{promptId}", response_model=ResultEntity)
async def delete_prompt(
        promptId: str = Path(..., description="提示词ID"),
        tenantId: str = Query(..., description="租户ID"),
        current_user_id: str = Depends(get_user_id_from_header),
        prompt_service: PromptService = Depends()
):
    """删除指定的提示词（需要验证租户和用户权限）"""
    return await prompt_service.delete_prompt(promptId, tenantId, current_user_id)


@router.put("/updatePrompt", response_model=ResultEntity)
async def update_prompt(
        prompt_data: UpdatePromptSchema = Body(..., description="更新提示词请求参数"),
        current_user_id: str = Depends(get_user_id_from_header),
        prompt_service: PromptService = Depends()
):
    """更新提示词记录"""
    return await prompt_service.update_prompt(prompt_data, current_user_id)