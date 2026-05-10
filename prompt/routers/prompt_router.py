from fastapi import APIRouter, Depends, Query, Body

from common.dependencies.auth_dependency import get_current_user
from common.schemas.user_schema import UserSchema
from common.utils.result_util import ResultEntity
from prompt.services.prompt_service import PromptService
from prompt.schemas.prompt_schema import UpdatePromptSchema

router = APIRouter(
    prefix="/service/prompt",
    tags=["prompt"],
    responses={404: {"description": "Not found"}},
)


@router.get("/getPrompt", response_model=ResultEntity)
async def get_prompt(
    tenantId: str = Query(..., description="租户ID"),
    current_user: UserSchema = Depends(get_current_user),
    prompt_service: PromptService = Depends()
):
    """
    根据租户ID查询提示词记录，如果不存在则自动创建默认提示词
    
    Args:
        tenantId: 租户ID
        current_user: 当前登录用户
        
    Returns:
        ResultEntity: 包含提示词记录的响应
    """
    return await prompt_service.get_prompt(tenantId, current_user)


@router.post("/updatePrompt", response_model=ResultEntity)
async def update_prompt(
    prompt_data: UpdatePromptSchema = Body(..., description="更新提示词请求参数"),
    current_user: UserSchema = Depends(get_current_user),
    prompt_service: PromptService = Depends()
):
    """
    更新提示词记录
    
    Args:
        prompt_data: 更新提示词请求参数，包含id、prompt、tenant_id
        current_user: 当前登录用户
        
    Returns:
        ResultEntity: 包含更新后的提示词记录的响应
        
    Example Request:
        POST /service/prompt/updatePrompt
        {
            "id": "abc123def456",
            "prompt": "你是一个专业的AI助手，请用友善的语气回答问题。",
            "tenant_id": "f96f89c075d611f0be3b002b67a509e7"
        }
    """
    return await prompt_service.update_prompt(prompt_data, current_user)