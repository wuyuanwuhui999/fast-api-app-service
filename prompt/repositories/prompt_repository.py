from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text

from common.utils.result_util import ResultEntity
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
    def get_system_prompt_list_by_category(self,  category_id: str,keyword:str, page_num: int, page_size: int) -> list[PromptSystemShema]:
        query = self.db.query(PromptSystemModel).filter(
            PromptSystemModel.disabled == 0
        )

        # 如果传了category_id就根据category_id查询
        if category_id:
            query = query.filter(PromptSystemModel.categoryId == category_id)
        # 如果keyword不为空，就根据keyword查询（模糊匹配提示词内容）
        if keyword:
            query = query.filter(PromptSystemModel.prompt.like(f"%{keyword}%"))
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
    def get_system_prompt_count_by_category(self, category_id: str,keyword:str) -> int:
        query = self.db.query(PromptSystemModel).filter(
            PromptSystemModel.disabled == 0
        )

        # 如果传了category_id就根据category_id查询
        if category_id:
            query = query.filter(PromptSystemModel.categoryId == category_id)

        # 如果keyword不为空，就根据keyword查询（模糊匹配提示词内容）
        if keyword:
            query = query.filter(PromptSystemModel.prompt.like(f"%{keyword}%"))

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

    def get_my_collect_prompt_category(self, tenant_id: str, user_id: str) -> list[PromptCategorySchema]:
        # 检查用户是否在当前租户内且启用状态
        # 假设有一个 tenant_user 表来管理租户用户关系
        # 这里需要根据你的实际表结构来调整

        # 方法1: 使用原生SQL查询（推荐）
        from sqlalchemy import text
        sql = text("""
            SELECT DISTINCT
                pc.id,
                pc.category,
                pc.create_time,
                pc.update_time
            FROM prompt_collect pcol
                     INNER JOIN prompt_category pc ON pcol.category_id = pc.id
            WHERE pcol.user_id = :user_id
                AND pcol.tenant_id = :tenant_id
              AND EXISTS (
                SELECT 1 FROM tenant_user tu
                WHERE tu.tenant_id = :tenant_id
                  AND tu.user_id = :user_id
                  AND tu.disabled = 0
            )
            ORDER BY pc.create_time DESC
        """)

        result = self.db.execute(sql, {
            'user_id': user_id,
            'tenant_id': tenant_id
        })

        categories = []
        for row in result:
            categories.append(PromptCategorySchema(
                id=row[0],
                category=row[1],
                create_time=row[2],
                update_time=row[3]
            ))
        return categories

    def get_my_collect_prompt_list(self, tenant_id: str, category_id: str, user_id: str, page_num: int,
                                   page_size: int) -> list[PromptCollectShema]:
        # 计算分页偏移量
        start = (page_num - 1) * page_size

        # 使用原生SQL查询，按照提供的SQL逻辑
        sql = text("""
            SELECT
                pc.id,
                pc.prompt_id,
                pc.user_id,
                pc.category_id,
                pc.tenant_id,
                pc.create_time,
                pc.update_time,
                ps.prompt,
                ps.disabled
            FROM prompt_collect pc
            INNER JOIN prompt_system ps ON pc.prompt_id = ps.id COLLATE utf8mb4_general_ci
            WHERE pc.user_id = :user_id
            AND pc.tenant_id = :tenant_id
        """)

        # 添加分类条件
        if category_id:
            sql = text(str(sql) + " AND pc.category_id = :category_id")

        # 添加租户用户检查
        sql = text(str(sql) + """
            AND EXISTS (
                SELECT 1 FROM tenant_user tu
                WHERE tu.tenant_id = :tenant_id COLLATE utf8mb4_general_ci
                AND tu.user_id = :user_id COLLATE utf8mb4_general_ci
                AND tu.disabled = 0
            )
            ORDER BY pc.create_time DESC
            LIMIT :start, :page_size
        """)

        # 准备参数
        params = {
            'user_id': user_id,
            'tenant_id': tenant_id,
            'start': start,
            'page_size': page_size
        }

        if category_id:
            params['category_id'] = category_id

        # 执行查询
        result = self.db.execute(sql, params)

        # 转换为Schema
        collects = []
        for row in result:
            # 创建一个包含所有字段的字典，包括从prompt_system表查询到的prompt字段
            collect_data = {
                'id': row[0],
                'prompt_id': row[1],
                'user_id': row[2],
                'category_id': row[3],
                'tenant_id': row[4],
                'create_time': row[5],
                'update_time': row[6],
                # 这里需要扩展PromptCollectShema来包含prompt字段，或者创建新的Schema
                'prompt': row[7],  # 从prompt_system表查询到的prompt
                'disabled': row[8]  # 从prompt_system表查询到的disabled
            }
            collects.append(PromptCollectShema(**collect_data))

        return collects

    # 查询收藏总数
    def get_my_collect_prompt_count(self, tenant_id: str, category_id: str, user_id: str) -> int:
        sql = text("""
            SELECT COUNT(*)
            FROM prompt_collect pc
            INNER JOIN prompt_system ps ON pc.prompt_id = ps.id COLLATE utf8mb4_general_ci
            WHERE pc.user_id = :user_id
            AND pc.tenant_id = :tenant_id
        """)

        # 添加分类条件
        if category_id:
            sql = text(str(sql) + " AND pc.category_id = :category_id")

        # 添加租户用户检查
        sql = text(str(sql) + """
            AND EXISTS (
                SELECT 1 FROM tenant_user tu
                WHERE tu.tenant_id = :tenant_id COLLATE utf8mb4_general_ci
                AND tu.user_id = :user_id COLLATE utf8mb4_general_ci
                AND tu.disabled = 0
            )
        """)

        # 准备参数
        params = {
            'user_id': user_id,
            'tenant_id': tenant_id
        }

        if category_id:
            params['category_id'] = category_id

        # 执行查询
        result = self.db.execute(sql, params)
        count = result.scalar()

        return count

    def _generate_id(self) -> str:
        """生成ID的辅助方法，你可以根据实际需求修改"""
        import uuid
        return str(uuid.uuid4().hex)