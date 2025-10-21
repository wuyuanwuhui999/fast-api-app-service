from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from prompt.models.prompt_model import PromptModel, PromptCategoryModel, PromptSystemModel, PromptCollectModel
from prompt.schemas.prompt_schema import PromptCategorySchema, PromptSystemShema, PromptCollectShema


class PromptRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_prompt_category_list(self) -> list[PromptCategorySchema]:
        categories = self.db.query(PromptCategoryModel).all()
        return [PromptCategorySchema(
            id=category.id,
            category=category.category,
            create_time=category.create_time,
            update_time=category.update_time
        ) for category in categories]

    # 查询提示词列表
    def get_system_prompt_list_by_category(self, tenant_id: str, category_id: str, user_id: str, page_num: int,
                                           page_size: int) -> list[PromptSystemShema]:
        query = self.db.query(PromptSystemModel).filter(
            PromptSystemModel.disabled == 0
        )

        # 如果传了category_id就根据category_id查询
        if category_id:
            query = query.filter(PromptSystemModel.categoryId == category_id)

        # 分页查询
        prompts = query.offset((page_num - 1) * page_size).limit(page_size).all()

        # 转换为Schema
        return [PromptSystemShema(
            id=prompt.id,
            categoryId=prompt.categoryId,
            prompt=prompt.prompt,
            disabled=prompt.disabled,
            create_time=prompt.create_time,
            update_time=prompt.update_time
        ) for prompt in prompts]

    # 查询提示词总数
    def get_system_prompt_count_by_category(self, tenant_id: str, category_id: str, user_id: str) -> int:
        query = self.db.query(PromptSystemModel).filter(
            PromptSystemModel.disabled == 0
        )

        # 如果传了category_id就根据category_id查询
        if category_id:
            query = query.filter(PromptSystemModel.categoryId == category_id)

        return query.count()

    def insert_collect_prompt(self, tenant_id: str, prompt_id: str, user_id: str) -> int:
        # 检查是否已经收藏
        existing_collect = self.db.query(PromptCollectModel).filter(
            and_(
                PromptCollectModel.tenant_id == tenant_id,
                PromptCollectModel.prompt_id == prompt_id,
                PromptCollectModel.user_id == user_id
            )
        ).first()

        if existing_collect:
            return 0  # 已经收藏过了

        # 获取系统提示词的category_id
        system_prompt = self.db.query(PromptSystemModel).filter(
            PromptSystemModel.id == prompt_id
        ).first()

        if not system_prompt:
            return -1  # 提示词不存在

        # 创建新的收藏记录
        new_collect = PromptCollectModel(
            id=self._generate_id(),  # 需要实现生成ID的方法
            prompt_id=prompt_id,
            category_id=system_prompt.categoryId,
            tenant_id=tenant_id,
            user_id=user_id
        )

        self.db.add(new_collect)
        self.db.commit()
        return 1

    def delete_collect_prompt(self, tenant_id: str, prompt_id: str, user_id: str) -> int:
        # 查找收藏记录
        collect_record = self.db.query(PromptCollectModel).filter(
            and_(
                PromptCollectModel.tenant_id == tenant_id,
                PromptCollectModel.prompt_id == prompt_id,
                PromptCollectModel.user_id == user_id
            )
        ).first()

        if not collect_record:
            return 0  # 收藏记录不存在

        self.db.delete(collect_record)
        self.db.commit()
        return 1

    def get_my_collect_prompt_list(self, tenant_id: str, category_id: str, user_id: str, page_num: int,
                                   page_size: int) -> list[PromptCollectShema]:
        query = self.db.query(PromptCollectModel).filter(
            and_(
                PromptCollectModel.tenant_id == tenant_id,
                PromptCollectModel.user_id == user_id
            )
        )

        # 如果category_id不为空，则根据category_id查询
        if category_id:
            query = query.filter(PromptCollectModel.category_id == category_id)

        # 分页查询
        collects = query.offset((page_num - 1) * page_size).limit(page_size).all()

        # 转换为Schema
        return [PromptCollectShema(
            id=collect.id,
            prompt_id=collect.prompt_id,
            category_id=collect.category_id,
            tenant_id=collect.tenant_id,
            user_id=collect.user_id,
            create_time=collect.create_time,
            update_time=collect.update_time
        ) for collect in collects]

    # 查询收藏总数
    def get_my_collect_prompt_count(self, tenant_id: str, category_id: str, user_id: str) -> int:
        query = self.db.query(PromptCollectModel).filter(
            and_(
                PromptCollectModel.tenant_id == tenant_id,
                PromptCollectModel.user_id == user_id
            )
        )

        # 如果category_id不为空，则根据category_id查询
        if category_id:
            query = query.filter(PromptCollectModel.category_id == category_id)

        return query.count()

    def _generate_id(self) -> str:
        """生成ID的辅助方法，你可以根据实际需求修改"""
        import uuid
        return str(uuid.uuid4().hex)