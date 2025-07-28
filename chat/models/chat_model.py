from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatModel(Base):
    __tablename__ = 'chat_model'
    __table_args__ = {
        'comment': '模型表',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_general_ci',
        'mysql_engine': 'InnoDB'
    }
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    model_name = Column(String(255), nullable=True, comment='模型名称')
    create_time = Column(DateTime, nullable=True, comment='创建时间')
    update_time = Column(DateTime, nullable=True, comment='更新时间')