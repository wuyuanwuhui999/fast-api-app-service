from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from common.schemas.user_schema import UserInDB
from user.repositories.user_repository import UserRepository
from user.schemas.user_schema import UserCreate, UserUpdate, PasswordChange, ResetPasswordConfirm, MailRequest, \
    TenantUserRoleSchema, TenantUserRoleUpdateSchema, TenantUpdateSchema, TenantCreateSchema
from common.config.common_database import get_db
from common.utils.jwt_util import create_access_token
from datetime import timedelta
from common.config.common_config import get_settings
import random
import redis
from fastapi.logger import logger
from common.utils.result_util import ResultEntity, ResultUtil

settings = get_settings()


class UserService:
    def __init__(self, db: Session = Depends(get_db)):
        self.user_repository = UserRepository(db)
        self.redis = redis.Redis.from_url(settings.redis_url)

    async def register_user(self, user: UserCreate) -> ResultEntity:
        if self.user_repository.get_user_by_user_account(user.user_account):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )

        if self.user_repository.get_user_by_email(user.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user_data = self.user_repository.create_user(user)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user_data).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def get_user_data(self, current_user: UserInDB) -> ResultEntity:
        user = self.user_repository.get_user_by_id(current_user.id)
        user_data = UserInDB.model_validate(user).dict()
        # 生成新的访问令牌，默认30天有效期
        token = create_access_token(data={"sub": user_data})

        # 直接返回封装好的ResultEntity
        return ResultUtil.success(
            data=user_data,
            token=token
        )

    async def update_user(self, user_id: str, user: UserUpdate) -> ResultEntity:
        db_user = self.user_repository.update_user(user_id, user)
        if db_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        return ResultUtil.success(data=1)

    async def update_password(self, user_account: str, password_change: PasswordChange) -> ResultEntity:
        # 使用同步调用
        user = self.user_repository.verify_password(user_account, password_change.oldPassword)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码不正确"
            )

        # 更新密码
        success = self.user_repository.update_password(user.id, password_change.newPassword)
        return ResultUtil.success(data=1 if success else 0)

    async def send_email_verify_code(self, mail_request: MailRequest) -> ResultEntity:
        if not self.user_repository.get_user_by_email(mail_request.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not registered"
            )

        code = random.randint(1000, 9999)
        await self.redis.setex(mail_request.email, timedelta(minutes=5), code)
        print(f"Verification code for {mail_request.email}: {code}")
        return ResultUtil.success(msg="验证码发送成功，请在五分钟内完成操作")

    async def reset_password(self, reset_request: ResetPasswordConfirm) -> ResultEntity:
        stored_code = self.redis.get(reset_request.email)
        if stored_code is None or stored_code.decode('utf-8') != reset_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        user = self.user_repository.get_user_by_email(reset_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        self.user_repository.update_password(user.id, reset_request.new_password)

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def login_by_email(self, mail_request: MailRequest) -> ResultEntity:
        stored_code = self.redis.get(mail_request.email)
        if stored_code is None or stored_code.decode('utf-8') != mail_request.code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code"
            )

        user = self.user_repository.get_user_by_email(mail_request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        user_data = UserInDB.model_validate(user).dict()
        access_token = create_access_token(
            data={"sub": user_data},
            expires_delta=access_token_expires
        )
        return ResultUtil.success(
            camel_data=user_data,
            token=access_token
        )

    async def verify_user(self, user: UserCreate) -> ResultEntity:
        user_account_count = self.user_repository.verify_user(user.user_account)
        return ResultUtil.success(data=user_account_count)

    async def get_user_tenants(self, user_id: str) -> ResultEntity:
        """获取用户所属的所有租户"""
        try:
            tenants = await self.user_repository.get_user_tenants(user_id)
            return ResultUtil.success(data=tenants, total=len(tenants))
        except Exception as e:
            logger.error(f"获取用户租户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg="获取租户列表失败")

    async def create_tenant(self, tenant_data: TenantCreateSchema, current_user: UserInDB) -> ResultEntity:
        if not await self._check_admin_permission(current_user.id):
            return ResultUtil.fail(msg="无权创建租户")

        try:
            tenant = await self.user_repository.create_tenant(tenant_data, current_user.id)
            return ResultUtil.success(data=tenant)
        except Exception as e:
            logger.error(f"创建租户失败: {str(e)}")
            return ResultUtil.fail(msg="创建租户失败")

    async def update_tenant(self, tenant_id: str, update_data: TenantUpdateSchema,
                            current_user: UserInDB) -> ResultEntity:
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权修改此租户")

        success = await self.user_repository.update_tenant(tenant_id, update_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def delete_tenant(self, tenant_id: str, current_user: UserInDB) -> ResultEntity:
        if not await self._check_super_admin(current_user.id):
            return ResultUtil.fail(msg="需要超级管理员权限")

        success = await self.user_repository.delete_tenant(tenant_id)
        return ResultUtil.success() if success else ResultUtil.fail(msg="租户不存在")

    async def manage_tenant_user(
            self,
            tenant_id: str,
            user_id: str,
            role_data: TenantUserRoleUpdateSchema,
            current_user: UserInDB
    ) -> ResultEntity:
        # 权限检查
        if not await self._check_tenant_admin(tenant_id, current_user.id):
            return ResultUtil.fail(msg="无权管理此租户用户")

        # 超级管理员才能设置管理员权限
        if role_data.role_type is not None and role_data.role_type >= 1:
            if not await self._check_super_admin(current_user.id):
                return ResultUtil.fail(msg="需要超级管理员权限设置管理员")

        # 更新用户角色
        full_data = TenantUserRoleSchema(
            tenant_id=tenant_id,
            user_id=user_id,
            **role_data.dict(exclude_unset=True)
        )

        success = await self.user_repository.set_tenant_user_role(full_data)
        return ResultUtil.success() if success else ResultUtil.fail(msg="操作失败")

    async def _check_admin_permission(self, user_id: str) -> bool:
        """检查用户是否有管理员权限（至少是某个租户的管理员）"""
        try:
            # 获取用户的所有租户角色
            tenant_roles = await self.user_repository.get_user_tenants(user_id)
            # 检查是否有至少一个租户的角色是管理员(1)或超级管理员(2)
            return any(tenant.role_type >= 1 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_super_admin(self, user_id: str) -> bool:
        """检查用户是否是超级管理员（任意租户的角色为2）"""
        try:
            # 获取用户的所有租户角色
            tenant_roles = await self.user_repository.get_user_tenants(user_id)
            # 检查是否有任意租户的角色是超级管理员(2)
            return any(tenant.role_type == 2 for tenant in tenant_roles)
        except Exception as e:
            logger.error(f"检查超级管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def _check_tenant_admin(self, tenant_id: str, user_id: str) -> bool:
        """检查用户是否是特定租户的管理员或超级管理员"""
        try:
            # 获取用户在该租户的角色
            tenant_roles = await self.user_repository.get_user_tenants(user_id)
            for tenant in tenant_roles:
                if tenant.id == tenant_id:
                    # 角色类型1(管理员)或2(超级管理员)都有权限
                    return tenant.role_type >= 1
            return False
        except Exception as e:
            logger.error(f"检查租户管理员权限失败: {str(e)}", exc_info=True)
            return False

    async def get_tenant_users(
            self,
            tenant_id: str,
            current_user: UserInDB
    ) -> ResultEntity:
        """获取租户下的所有用户（需要租户管理员权限）"""
        try:
            # 权限检查 - 只有租户管理员或超级管理员可以查看
            if not await self._check_tenant_admin(tenant_id, current_user.id):
                return ResultUtil.error("无权查看此租户用户列表")

            # 获取租户用户列表
            users = await self.chat_repository.get_tenant_users(tenant_id)

            # 获取用户详细信息（从用户表）
            user_details = []
            for user_role in users:
                user = await self.user_repository.get_user(user_role.user_id)
                if user:
                    user_details.append({
                        **user_role.dict(),
                        "username": user.username,
                        "email": user.email,
                        "avatar": user.avatar
                    })

            return ResultUtil.success(data=user_details)

        except Exception as e:
            logger.error(f"获取租户用户列表失败: {str(e)}", exc_info=True)
            return ResultUtil.error("获取用户列表失败")