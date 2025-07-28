from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatDocDirectory(Base):
    __tablename__ = 'chat_doc_directory'
    __table_args__ = {
        'comment': '文档目录',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_general_ci',
        'mysql_engine': 'InnoDB'
    }
    id = Column(String(64), primary_key=True, comment='租户id')  # 字符串类型主键
    user_id = Column(String(64), nullable=True, comment='用户id')  # 可为空的字符串字段
    directory = Column(String(255), nullable=False, comment='目录')  # 非空的字符串字段
    create_time = Column(DateTime, nullable=True, comment='创建时间')  # 可为空的日期时间字段
    update_time = Column(DateTime, nullable=True, comment='更新时间')  # 可为空的日期时间字段