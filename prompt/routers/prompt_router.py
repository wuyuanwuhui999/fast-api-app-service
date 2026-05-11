from fastapi import APIRouter, Depends, Query, Body, Header, HTTPException
from common.utils.result_util import ResultEntity
from prompt.services.prompt_service import PromptService
from prompt.schemas.prompt_schema import UpdatePromptSchema


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
    current_user_id: str = Depends(get_user_id_from_header),
    prompt_service: PromptService = Depends()
):
    """根据租户ID查询提示词记录"""
    return await prompt_service.get_prompt(tenantId, current_user_id)


@router.post("/updatePrompt", response_model=ResultEntity)
async def update_prompt(
    prompt_data: UpdatePromptSchema = Body(..., description="更新提示词请求参数"),
    current_user_id: str = Depends(get_user_id_from_header),
    prompt_service: PromptService = Depends()
):
    """更新提示词记录"""
    return await prompt_service.update_prompt(prompt_data, current_user_id)