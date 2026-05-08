from fastapi import APIRouter, Depends, Query

from common.dependencies.auth_dependency import get_current_user
from common.schemas.user_schema import UserSchema
from common.utils.result_util import ResultEntity
from prompt.services.prompt_service import PromptService

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