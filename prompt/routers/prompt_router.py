from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..dependencies import get_db
from prompt.schemas.prompt_schema import PromptCreateSchema, PromptUpdateSchema, Prompt
from prompt.services.prompt_service import PromptService

router = APIRouter(
    prefix="/prompts",
    tags=["prompts"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=Prompt, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    prompt_create: PromptCreateSchema,
    prompt_service: PromptService = Depends()
):
    return prompt_service.create_prompt(prompt_create)

@router.get("/", response_model=List[Prompt])
async def read_prompts(
    skip: int = 0,
    limit: int = 100,
    prompt_service: PromptService = Depends()
):
    return prompt_service.get_prompts(skip, limit)

@router.get("/{prompt_id}", response_model=Prompt)
async def read_prompt(
    prompt_id: str,
    prompt_service: PromptService = Depends()
):
    prompt = prompt_service.get_prompt(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return prompt

@router.put("/{prompt_id}", response_model=Prompt)
async def update_prompt(
    prompt_id: str,
    prompt_update: PromptUpdateSchema,
    prompt_service: PromptService = Depends()
):
    prompt = prompt_service.update_prompt(prompt_id, prompt_update)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return prompt

@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: str,
    prompt_service: PromptService = Depends()
):
    if not prompt_service.delete_prompt(prompt_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found"
        )
    return None

@router.get("/search/", response_model=List[Prompt])
async def search_prompts(
    keyword: str,
    skip: int = 0,
    limit: int = 100,
    prompt_service: PromptService = Depends()
):
    return prompt_service.search_prompts(keyword, skip, limit)