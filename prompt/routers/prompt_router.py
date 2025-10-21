from fastapi import APIRouter, Depends

from common.dependencies.auth_dependency import get_current_user
from common.schemas.user_schema import UserSchema
from common.utils.result_util import ResultEntity
from prompt.services.prompt_service import PromptService

router = APIRouter(
    prefix="/service/prompt",
    tags=["prompt"],
    responses={404: {"description": "Not found"}},
)

@router.get("/getPromptCategoryList",response_model=ResultEntity)
async def get_prompt_category_list(
    prompt_service: PromptService = Depends()
):
    return await prompt_service.get_prompt_category_list()


@router.get("/getSystemPromptListByCategory",response_model=ResultEntity)
async def get_system_prompt_list_by_category(
        categoryId: str = None,
        keyword:str = None,
        pageNum: int = 1,
        pageSize: int = 10,
        prompt_service: PromptService = Depends()
):
    return await prompt_service.get_system_prompt_list_by_category( categoryId, keyword, pageNum, pageSize)

@router.post("/insertCollectPrompt/{tenantId}/{promptId}",response_model=ResultEntity)
async def insert_collect_prompt(
        tenantId: str,
        promptId: str,
        current_user: UserSchema = Depends(get_current_user),
        prompt_service: PromptService = Depends()
):
    return await prompt_service.insert_collect_prompt(tenantId, promptId,current_user.id)

@router.delete("/deleteCollectPrompt/{tenantId}/{promptId}",response_model=ResultEntity)
async def delete_collect_prompt(
        tenantId: str,
        promptId: str,
        current_user: UserSchema = Depends(get_current_user),
        prompt_service: PromptService = Depends()
):
    return await prompt_service.delete_collect_prompt(tenantId, promptId,current_user.id)

@router.get("/getMyCollectPromptCategory",response_model=ResultEntity)
async def get_my_collect_prompt_category(
        tenantId: str,
        current_user: UserSchema = Depends(get_current_user),
        prompt_service: PromptService = Depends()
):
    return await prompt_service.get_my_collect_prompt_category(tenantId, current_user.id)

@router.get("/getMyCollectPromptList",response_model=ResultEntity)
async def get_my_collect_prompt_list(
        tenantId: str,
        categoryId: str = None,
        pageNum: int = 1,
        pageSize: int = 10,
        current_user: UserSchema = Depends(get_current_user),
        prompt_service: PromptService = Depends()
):
    return await prompt_service.get_my_collect_prompt_list(tenantId, categoryId, current_user.id,pageNum,pageSize)