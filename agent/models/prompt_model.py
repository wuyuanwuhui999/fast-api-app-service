# prompt/models/prompt_model.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class PromptModel(Base):
    __tablename__ = 'prompt'
    __table_args__ = {
        'comment': '提示词表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }

    id = Column(String(32), primary_key=True, comment='主键ID')
    prompt = Column(String(255), nullable=False, comment='提示词内容')
    tenant_id = Column(String(32), nullable=False, comment='租户ID')
    user_id = Column(String(32), nullable=False, comment='用户ID')
    create_time = Column(DateTime, comment='创建时间')
    update_time = Column(DateTime, comment='更新时间')

    def __repr__(self):
        return f"<Prompt(id={self.id}, prompt={self.prompt[:20]})>"