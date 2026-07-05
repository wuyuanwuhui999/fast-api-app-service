# prompt/services/prompt_service.py
from typing import Optional, List
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from prompt.models.prompt_model import PromptModel
from prompt.schemas.prompt_schema import PromptSchema, UpdatePromptSchema, InsertPromptSchema
from prompt.repositories.prompt_repository import PromptRepository


class PromptService:
    def __init__(self, db: Session = Depends(get_db)):
        self.repository = PromptRepository(db)

    async def get_prompt(
            self,
            tenant_id: str,
            current_user_id: str,
            prompt_id: Optional[str] = None
    ) -> ResultEntity:
        """
        查询提示词记录

        当 prompt_id 不为空时：根据ID精确查询单条提示词（同时校验租户和用户权限）
        当 prompt_id 为空时：根据租户ID查询，如果不存在则创建默认提示词

        Args:
            tenant_id: 租户ID
            current_user_id: 当前登录用户ID
            prompt_id: 提示词ID（可选）

        Returns:
            ResultEntity: 提示词记录
        """
        try:
            # 验证租户ID
            if not tenant_id:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)

            # 如果传入了 prompt_id，根据ID精确查询
            if prompt_id:
                # 验证 prompt_id 不能为空字符串
                if not prompt_id.strip():
                    return ResultUtil.fail(msg="提示词ID不能为空", data=None)

                # 查询指定ID的提示词（校验租户和用户权限）
                prompt = await self.repository.get_prompt_by_id(
                    prompt_id=prompt_id,
                    tenant_id=tenant_id,
                    user_id=current_user_id
                )

                if not prompt:
                    return ResultUtil.fail(
                        msg="提示词不存在或无权访问",
                        data=None
                    )

                return ResultUtil.success(data=prompt)

            # 没有传入 prompt_id，根据 tenant_id 查询或创建默认提示词
            prompt = await self.repository.get_prompt_by_tenant(tenant_id)

            # 如果没有查到数据，则创建默认提示词
            if not prompt:
                logger.info(f"租户 {tenant_id} 未找到提示词，正在创建默认提示词...")
                prompt = await self.repository.create_default_prompt(tenant_id, current_user_id)

                if not prompt:
                    return ResultUtil.fail(msg="创建默认提示词失败", data=None)

                return ResultUtil.success(data=prompt, msg="已创建默认提示词")

            return ResultUtil.success(data=prompt)

        except Exception as e:
            logger.error(f"获取提示词失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取提示词失败: {str(e)}", data=None)

    async def get_prompt_list(
            self,
            tenant_id: str,
            current_user_id: str,
            keyword: Optional[str] = None,
            page_num: int = 1,
            page_size: int = 10
    ) -> ResultEntity:
        """
        分页获取当前租户下当前用户的所有提示词列表
        支持按关键词模糊搜索提示词内容

        Args:
            tenant_id: 租户ID
            current_user_id: 当前登录用户ID
            keyword: 搜索关键词（可选），对 prompt 字段进行模糊匹配
            page_num: 页码，从1开始
            page_size: 每页数量

        Returns:
            ResultEntity: 提示词列表（包含分页信息）
        """
        try:
            # 验证租户ID
            if not tenant_id:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)

            # 验证分页参数
            if page_num < 1:
                page_num = 1
            if page_size < 1:
                page_size = 10
            if page_size > 100:
                page_size = 100

            # 查询提示词列表
            prompt_list, total = await self.repository.get_prompt_list_by_tenant(
                tenant_id=tenant_id,
                user_id=current_user_id,
                keyword=keyword,
                page=page_num,
                page_size=page_size
            )

            return ResultUtil.success(data=prompt_list, total=total)

        except Exception as e:
            logger.error(f"获取提示词列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取提示词列表失败: {str(e)}", data=None)

    async def insert_prompt(self, prompt_data: InsertPromptSchema, current_user_id: str) -> ResultEntity:
        """
        插入新提示词

        Args:
            prompt_data: 插入提示词请求数据
            current_user_id: 当前登录用户ID

        Returns:
            ResultEntity: 插入结果
        """
        try:
            # 验证必填字段
            if not prompt_data.prompt or not prompt_data.prompt.strip():
                return ResultUtil.fail(msg="提示词内容不能为空", data=None)

            if len(prompt_data.prompt) > 255:
                return ResultUtil.fail(msg="提示词内容不能超过255个字符", data=None)

            if not prompt_data.tenantId:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)

            # 插入提示词
            inserted_prompt = await self.repository.insert_prompt(
                prompt_text=prompt_data.prompt.strip(),
                tenant_id=prompt_data.tenantId,
                user_id=current_user_id
            )

            if not inserted_prompt:
                return ResultUtil.fail(msg="插入提示词失败", data=None)

            return ResultUtil.success(data=1, msg="提示词插入成功")

        except Exception as e:
            logger.error(f"插入提示词失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"插入提示词失败: {str(e)}", data=None)

    async def delete_prompt(self, prompt_id: str, tenant_id: str, current_user_id: str) -> ResultEntity:
        """
        删除提示词

        Args:
            prompt_id: 提示词ID
            tenant_id: 租户ID
            current_user_id: 当前登录用户ID

        Returns:
            ResultEntity: 删除结果
        """
        try:
            # 验证必填字段
            if not prompt_id:
                return ResultUtil.fail(msg="提示词ID不能为空", data=None)

            if not tenant_id:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)

            # 检查提示词是否存在且有权限
            existing_prompt = await self.repository.get_prompt_by_id(prompt_id, tenant_id)

            if not existing_prompt:
                return ResultUtil.fail(msg="提示词不存在或无权删除", data=None)

            # 删除提示词
            success = await self.repository.delete_prompt_by_id(prompt_id, tenant_id, current_user_id)

            if not success:
                return ResultUtil.fail(msg="删除提示词失败", data=None)

            return ResultUtil.success(data=1, msg="提示词删除成功")

        except Exception as e:
            logger.error(f"删除提示词失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"删除提示词失败: {str(e)}", data=None)

    async def update_prompt(self, prompt_data: UpdatePromptSchema, current_user_id: str) -> ResultEntity:
        """
        更新提示词记录

        Args:
            prompt_data: 更新提示词请求数据
            current_user_id: 当前登录用户ID

        Returns:
            ResultEntity: 更新后的提示词记录
        """
        try:
            # 验证必填字段
            if not prompt_data.id:
                return ResultUtil.fail(msg="提示词ID不能为空", data=None)

            if not prompt_data.prompt or not prompt_data.prompt.strip():
                return ResultUtil.fail(msg="提示词内容不能为空", data=None)

            if len(prompt_data.prompt) > 255:
                return ResultUtil.fail(msg="提示词内容不能超过255个字符", data=None)

            if not prompt_data.tenant_id:
                return ResultUtil.fail(msg="租户ID不能为空", data=None)

            # 验证提示词是否存在且有权限修改
            existing_prompt = await self.repository.get_prompt_by_id(
                prompt_data.id,
                prompt_data.tenant_id
            )

            if not existing_prompt:
                return ResultUtil.fail(
                    msg="提示词记录不存在或无权修改",
                    data=None
                )

            # 更新提示词
            updated_prompt = await self.repository.update_prompt(
                prompt_data,
                current_user_id
            )

            if not updated_prompt:
                return ResultUtil.fail(msg="更新提示词失败", data=None)

            return ResultUtil.success(
                data=updated_prompt,
                msg="提示词更新成功"
            )

        except Exception as e:
            logger.error(f"更新提示词失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"更新提示词失败: {str(e)}", data=None)