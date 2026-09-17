"""chat 模块工具集（租户 / 公司成员管理）

与 Spring Boot 侧 `ChatTool` 对齐的安全设计：
- 操作者（当前登录用户）、当前租户 tenant_id、当前公司 company_id 在 build_chat_tools 时
  通过闭包绑定，绝不作为工具参数暴露给大模型，避免模型伪造操作者身份越权。
- 大模型只能决定「目标用户标识 targetUser」，服务端解析为 userId 后再操作。
- 每项写操作先做 Python 层权限校验（返回清晰中文提示），再执行带权限条件约束的 SQL（双重防越权）。

角色模型（与 Spring 侧差异需注意）：
- tenant_user.role：0-普通用户，1-租户管理员，2-超级管理员（与 Spring 一致）。
- company_user.role：字符串类型，0-普通成员，1-管理员，2-人事，3-企业老板（FastAPI 特有 4 级）。
"""
from typing import List, Optional
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session
from langchain_core.tools import tool, BaseTool


def build_chat_tools(
        db: Session,
        operator_user_id: str,
        tenant_id: Optional[str],
        company_id: Optional[str]
) -> List[BaseTool]:
    """根据当前请求上下文构建工具列表（每次请求新建，绑定操作者上下文）。"""

    # ---------------- 内部辅助函数（闭包捕获上下文） ----------------

    def _resolve_user(identifier: str) -> Optional[str]:
        """按用户ID / 用户账号 user_account / 用户名精确解析 userId；未找到或不唯一返回 None。"""
        if not identifier or not identifier.strip():
            return None
        rows = db.execute(
            text("SELECT id FROM `user` WHERE disabled = 0 "
                 "AND (id = :i OR user_account = :i OR username = :i)"),
            {"i": identifier.strip()}
        ).fetchall()
        if len(rows) != 1:
            return None
        return rows[0][0]

    def _check_tenant_super_admin() -> bool:
        n = db.execute(
            text("SELECT COUNT(*) FROM tenant_user WHERE tenant_id = :t AND user_id = :u "
                 "AND role = 2 AND disabled = 0"),
            {"t": tenant_id, "u": operator_user_id}
        ).scalar()
        return (n or 0) > 0

    def _check_tenant_admin() -> bool:
        n = db.execute(
            text("SELECT COUNT(*) FROM tenant_user WHERE tenant_id = :t AND user_id = :u "
                 "AND role IN (1, 2) AND disabled = 0"),
            {"t": tenant_id, "u": operator_user_id}
        ).scalar()
        return (n or 0) > 0

    def _check_tenant_member() -> bool:
        n = db.execute(
            text("SELECT COUNT(*) FROM tenant_user WHERE tenant_id = :t AND user_id = :u "
                 "AND disabled = 0"),
            {"t": tenant_id, "u": operator_user_id}
        ).scalar()
        return (n or 0) > 0

    def _get_tenant_user_role(target_user_id: str) -> Optional[int]:
        r = db.execute(
            text("SELECT role FROM tenant_user WHERE tenant_id = :t AND user_id = :u "
                 "AND disabled = 0 LIMIT 1"),
            {"t": tenant_id, "u": target_user_id}
        ).scalar()
        return int(r) if r is not None else None

    def _get_company_user_role(user_id: str) -> Optional[int]:
        r = db.execute(
            text("SELECT CAST(role AS UNSIGNED) FROM company_user WHERE company_id = :c "
                 "AND user_id = :u AND status = 1 LIMIT 1"),
            {"c": company_id, "u": user_id}
        ).scalar()
        return int(r) if r is not None else None

    def _set_tenant_user_role(target_user_id: str, role: int) -> int:
        """原子更新租户用户角色，SQL 内部强制操作者为超级管理员（role=2），防越权。"""
        result = db.execute(
            text("""
                UPDATE tenant_user tu
                JOIN tenant_user admin
                    ON admin.tenant_id = :t
                   AND admin.user_id = :a
                   AND admin.role = 2
                   AND admin.disabled = 0
                SET tu.role = :role, tu.create_by = :a
                WHERE tu.tenant_id = :t
                  AND tu.user_id = :u
                  AND tu.disabled = 0
            """),
            {"t": tenant_id, "u": target_user_id, "a": operator_user_id, "role": role}
        )
        db.commit()
        return result.rowcount or 0

    def _add_tenant_user(target_user_id: str) -> int:
        """原子添加租户用户（role=0），SQL 内部强制操作者为管理员（role IN 1,2），防越权。"""
        result = db.execute(
            text("""
                INSERT INTO tenant_user (id, tenant_id, user_id, role, join_date, create_by, disabled)
                SELECT :id, :t, :u, 0, NOW(), :a, 0
                FROM dual
                WHERE EXISTS (
                    SELECT 1 FROM tenant_user admin
                    WHERE admin.tenant_id = :t
                      AND admin.user_id = :a
                      AND admin.role IN (1, 2)
                      AND admin.disabled = 0
                )
                AND NOT EXISTS (
                    SELECT 1 FROM tenant_user tu
                    WHERE tu.tenant_id = :t
                      AND tu.user_id = :u
                )
            """),
            {"id": uuid.uuid4().hex, "t": tenant_id, "u": target_user_id, "a": operator_user_id}
        )
        db.commit()
        return result.rowcount or 0

    def _delete_tenant_user(target_user_id: str) -> int:
        """原子移除租户用户，SQL 内部强制操作者为管理员（role IN 1,2）且不能移除自己。"""
        result = db.execute(
            text("""
                DELETE tu FROM tenant_user tu
                JOIN tenant_user admin
                    ON admin.tenant_id = :t
                   AND admin.user_id = :a
                   AND admin.role IN (1, 2)
                   AND admin.disabled = 0
                WHERE tu.tenant_id = :t
                  AND tu.user_id = :u
                  AND tu.user_id != :a
            """),
            {"t": tenant_id, "u": target_user_id, "a": operator_user_id}
        )
        db.commit()
        return result.rowcount or 0

    def _delete_company_user(target_user_id: str) -> int:
        """原子移除公司员工，SQL 内部强制操作者为管理员（role>=1）且不能移除自己。"""
        result = db.execute(
            text("""
                DELETE cu FROM company_user cu
                JOIN company_user admin
                    ON admin.company_id = :c
                   AND admin.user_id = :a
                   AND CAST(admin.role AS UNSIGNED) >= 1
                   AND admin.status = 1
                WHERE cu.company_id = :c
                  AND cu.user_id = :u
                  AND cu.user_id != :a
            """),
            {"c": company_id, "u": target_user_id, "a": operator_user_id}
        )
        db.commit()
        return result.rowcount or 0

    # ---------------- 工具定义 ----------------

    @tool
    async def set_tenant_admin(targetUser: str) -> str:
        """把指定用户设置为当前租户的管理员。仅当前租户的超级管理员可以执行。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        if not _check_tenant_super_admin():
            return "无权限：设置租户管理员需要超级管理员权限"
        if _set_tenant_user_role(target_user_id, 1) > 0:
            return "已成功将该用户设置为当前租户的管理员"
        return "设置失败：目标用户可能不在当前租户中或已被禁用"

    @tool
    async def add_user_to_tenant(targetUser: str) -> str:
        """把指定用户添加到当前租户（作为普通成员）。需要普通管理员权限。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        if not _check_tenant_admin():
            return "无权限：添加租户用户需要普通管理员权限"
        if _get_tenant_user_role(target_user_id) is not None:
            return "该用户已在当前租户中"
        if _add_tenant_user(target_user_id) > 0:
            return "已成功将该用户添加到当前租户"
        return "添加失败：请检查目标用户状态"

    @tool
    async def add_user_to_tenant_as_admin(targetUser: str) -> str:
        """把指定用户添加到当前租户，并将其设置为管理员。添加需要普通管理员权限、设置管理员需要超级管理员权限，因此该操作需要超级管理员。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        if not _check_tenant_super_admin():
            return "无权限：添加用户并设置为管理员需要超级管理员权限"
        if _get_tenant_user_role(target_user_id) is None:
            if _add_tenant_user(target_user_id) <= 0:
                return "添加用户到租户失败"
        if _set_tenant_user_role(target_user_id, 1) > 0:
            return "已成功添加用户到当前租户并设置为管理员"
        return "设置管理员失败，请检查目标用户状态"

    @tool
    async def cancel_tenant_admin(targetUser: str) -> str:
        """取消指定用户在当前租户的管理员权限。仅当前租户的超级管理员可以执行。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        if not _check_tenant_super_admin():
            return "无权限：取消租户管理员需要超级管理员权限"
        if _set_tenant_user_role(target_user_id, 0) > 0:
            return "已成功取消该用户的租户管理员权限"
        return "取消失败：目标用户可能不在当前租户中或已被禁用"

    @tool
    async def remove_user_from_tenant(targetUser: str) -> str:
        """把指定用户移出当前租户。需要普通管理员权限。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        if not _check_tenant_admin():
            return "无权限：移除租户用户需要普通管理员权限"
        if operator_user_id == target_user_id:
            return "不能移除自己"
        if _delete_tenant_user(target_user_id) > 0:
            return "已成功将该用户移出当前租户"
        return "移除失败：用户不在当前租户中或无权操作"

    @tool
    async def count_tenant_users() -> str:
        """查询当前租户内有多少名成员。"""
        if not tenant_id:
            return "当前会话缺少租户上下文，无法执行租户操作"
        if not _check_tenant_member():
            return "无权限：你不是当前租户的成员"
        n = db.execute(
            text("SELECT COUNT(*) FROM tenant_user WHERE tenant_id = :t AND disabled = 0"),
            {"t": tenant_id}
        ).scalar()
        return f"当前租户内共有 {n or 0} 名成员"

    @tool
    async def count_company_employees() -> str:
        """查询当前公司内有多少名员工。"""
        if not company_id:
            return "当前会话缺少公司上下文，无法执行公司操作"
        if _get_company_user_role(operator_user_id) is None:
            return "无权限：你不是当前公司的成员"
        n = db.execute(
            text("SELECT COUNT(*) FROM company_user WHERE company_id = :c AND status = 1"),
            {"c": company_id}
        ).scalar()
        return f"当前公司内共有 {n or 0} 名员工"

    @tool
    async def remove_user_from_company(targetUser: str) -> str:
        """把指定用户移出当前公司。需要公司管理员权限，且不能移除自己或角色不低于自己的用户。
参数 targetUser：目标用户标识，可以是用户ID、用户账号(user_account)或用户名。"""
        if not company_id:
            return "当前会话缺少公司上下文，无法执行公司操作"
        target_user_id = _resolve_user(targetUser)
        if not target_user_id:
            return "未找到目标用户或用户标识不唯一，请用户提供更精确的用户ID、账号或用户名"
        operator_role = _get_company_user_role(operator_user_id)
        if operator_role is None or operator_role < 1:
            return "无权限：移除公司员工需要公司管理员权限"
        if operator_user_id == target_user_id:
            return "不能移除自己"
        target_role = _get_company_user_role(target_user_id)
        if target_role is None:
            return "目标用户不在当前公司中"
        # 企业老板(3)可移除任何人；其余角色不能移除角色不低于自己的用户
        if operator_role < 3 and target_role >= operator_role:
            return "无权限：不能移除角色高于或等于自己的用户"
        if _delete_company_user(target_user_id) > 0:
            return "已成功将该用户移出当前公司"
        return "移除失败：请检查目标用户状态"

    return [
        set_tenant_admin,
        add_user_to_tenant,
        add_user_to_tenant_as_admin,
        cancel_tenant_admin,
        remove_user_from_tenant,
        count_tenant_users,
        count_company_employees,
        remove_user_from_company,
    ]
