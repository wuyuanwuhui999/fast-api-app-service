from sqlalchemy import Column, String, Integer, DateTime, Boolean, SmallInteger, func
from common.config.common_database import Base
from pydantic import BaseModel

class LoginForm(BaseModel):
    userAccount: str
    password: str



class TenantModel(Base):
    __tablename__ = 'tenant'
    __table_args__ = {
        'comment': '租户表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }

    id = Column(String(32), primary_key=True, comment='租户ID')
    name = Column(String(100), nullable=False, comment='租户名称')
    code = Column(String(50), nullable=False, comment='租户编码')
    description = Column(String(255), comment='租户描述')
    status = Column(SmallInteger, default=1, comment='状态：0-禁用，1-启用')
    create_date = Column(DateTime, nullable=False, comment='创建时间')
    update_date = Column(DateTime, comment='更新时间')
    created_by = Column(String(32), nullable=False, comment='创建人ID')
    updated_by = Column(String(32), comment='更新人ID')


class TenantUserModel(Base):
    __tablename__ = 'tenant_user'
    __table_args__ = {
        'comment': '租户用户关联表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }

    id = Column(String(32), primary_key=True, comment='主键ID')
    tenant_id = Column(String(32), nullable=False, comment='租户ID')
    user_id = Column(String(32), nullable=False, comment='用户ID')
    role_type = Column(SmallInteger, nullable=False, comment='角色类型：0-普通用户，1-租户管理员，2-超级管理员')
    join_date = Column(DateTime, nullable=False, comment='加入时间')
    create_by = Column(String(32), nullable=False, comment='创建人ID')


# 在chat_model.py中添加以下模型（如果尚未存在）
class TenantUserRoleModel(Base):
    __tablename__ = 'tenant_user_role'
    __table_args__ = {
        'comment': '租户用户角色表',
        'mysql_charset': 'utf8mb4'
    }

    id = Column(String(32), primary_key=True)
    tenant_id = Column(String(32), nullable=False)
    user_id = Column(String(32), nullable=False)
    role_type = Column(Integer, nullable=False, comment='0-普通用户 1-管理员 2-超级管理员')
    is_disabled = Column(Boolean, default=False, comment='是否禁用')
    create_time = Column(DateTime, server_default=func.now())
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now())