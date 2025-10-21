from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

class PromptModel(Base):
    __tablename__ = 'prompt'

    id = Column(String(32), primary_key=True, comment='主键ID')
    tenant_id = Column(String(32), ForeignKey('tenant.id'), nullable=False, comment='租户ID')
    user_id = Column(String(32), ForeignKey('user.id'), nullable=False, comment='用户ID')
    title = Column(String(100), nullable=False, comment='提示词标题')
    content = Column(Text, nullable=False, comment='提示词内容')
    disabled = Column(TINYINT, default=0, nullable=False, comment='是否禁用：0-启用，1-禁用')
    industry = Column(String(50), nullable=True, comment='适用行业')
    tags = Column(String(255), nullable=True, comment='提示词标签')
    create_date = Column(DateTime, server_default=func.now(), nullable=False, comment='创建时间')
    update_date = Column(DateTime, onupdate=func.now(), nullable=True, comment='更新时间')
    created_by = Column(String(32), nullable=False, comment='创建人ID')
    updated_by = Column(String(32), nullable=True, comment='更新人ID')

    # 定义关系（可选）
    tenant = relationship("Tenant", back_populates="prompts")
    user = relationship("UserMode", back_populates="prompts")

    def __repr__(self):
        return f"<Prompt(id={self.id}, title={self.title})>"


class PromptCategoryModel(Base):
    __tablename__ = "prompt_category"

    id = Column(String(32), primary_key=True, comment="组件ID")
    category = Column(String(255), nullable=True, comment="提示词类别")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<PromptCategory(id='{self.id}', category='{self.category}')>"


class PromptSystemModel(Base):
    __tablename__ = "prompt_system"

    id = Column(String(64), primary_key=True, comment="主键ID")
    categoryId = Column(String(32), nullable=True, comment="分类id")
    prompt = Column(Text, nullable=False, comment="提示词内容")
    disabled = Column(Integer, nullable=False, default=0, comment="是否禁用：0-启用，1-禁用")
    create_time = Column(DateTime, nullable=False, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 如果需要关联查询，可以添加关系（可选）
    # category = relationship("PromptCategory", back_populates="prompt_systems")

    def __repr__(self):
        return f"<PromptSystem(id='{self.id}', categoryId='{self.categoryId}', disabled={self.disabled})>"


class PromptCollectModel(Base):
    __tablename__ = "prompt_collect"

    id = Column(String(32), primary_key=True, comment="主键")
    prompt_id = Column(String(32), nullable=True, comment="提示词id")
    category_id = Column(String(32), nullable=True, comment="分类id")
    tenant_id = Column(String(32), nullable=True, comment="租户id")
    user_id = Column(String(32), nullable=True, comment="用户id")
    create_time = Column(DateTime, default=datetime.now, comment="创建时间")
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更改时间")

    def __repr__(self):
        return f"<PromptCollect(id='{self.id}', user_id='{self.user_id}', prompt_id='{self.prompt_id}')>"