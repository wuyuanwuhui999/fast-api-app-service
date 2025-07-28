from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatHistory(Base):
    __tablename__ = 'chat_history'
    __table_args__ = {
        'comment': '聊天记录',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_general_ci',
        'mysql_engine': 'InnoDB'
    }
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键')
    user_id = Column(String(64), nullable=True, comment='用户id')
    model_name = Column(String(64), nullable=True, comment='模型名称')
    files = Column(String(1000), nullable=True, comment='文件')
    chat_id = Column(String(128), nullable=True, comment='会话id')
    prompt = Column(Text, nullable=True, comment='问题')
    think_content = Column(Text, nullable=True, comment='思考内容')
    response_content = Column(Text, nullable=True, comment='正文')
    content = Column(Text, nullable=True, comment='回复内容')
    create_time = Column(DateTime, nullable=True, comment='创建时间')