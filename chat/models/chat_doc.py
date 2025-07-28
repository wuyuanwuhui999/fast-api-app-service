from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatDoc(Base):
    __tablename__ = 'chat_doc'

    id = Column(String(32), primary_key=True, comment='文档id')  # 字符串类型主键
    directory_id = Column(String(255), nullable=True, comment='租户id')  # 可为空的字符串字段
    name = Column(String(255), nullable=True, comment='文档原标题')  # 可为空的字符串字段
    ext = Column(String(255), nullable=True, comment='文档格式')  # 可为空的字符串字段
    user_id = Column(String(32), nullable=True, comment='用户id')  # 可为空的字符串字段
    create_time = Column(DateTime, nullable=True, comment='更新时间')  # 可为空的日期时间字段（SQL中ON UPDATE CURRENT_TIMESTAMP会自动更新）
    update_time = Column(DateTime, nullable=True, comment='修改时间')  # 可为空的日期时间字段（SQL中ON UPDATE CURRENT_TIMESTAMP会自动更新）