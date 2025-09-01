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