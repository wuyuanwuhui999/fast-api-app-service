from sqlalchemy import Column, String, DateTime, Integer, Text, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ChatDocModel(Base):
    __tablename__ = 'chat_doc'
    __table_args__ = {
        'comment': '用户上传的RAG文档',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }

    id = Column(String(32), primary_key=True, comment='文档id')
    directory_id = Column(String(255), comment='目录id')  # 修改注释
    name = Column(String(255), comment='文档原标题')
    ext = Column(String(255), comment='文档格式')
    user_id = Column(String(32), comment='用户id')
    tenant_id = Column(String(32), comment='租户id')  # 新增tenant_id字段
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='修改时间')

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
    tenant_id = Column(String(255), nullable=False, comment='租户id')  # 非空的字符串字段
    create_time = Column(DateTime, nullable=True, comment='创建时间')  # 可为空的日期时间字段
    update_time = Column(DateTime, nullable=True, comment='更新时间')  # 可为空的日期时间字段


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
    system_prompt = Column(Text,nullable=True, comment='系统提示词')
    think_content = Column(Text, nullable=True, comment='思考内容')
    response_content = Column(Text, nullable=True, comment='正文')
    content = Column(Text, nullable=True, comment='回复内容')
    create_time = Column(DateTime, nullable=True, comment='创建时间')

class ChatModel(Base):
    __tablename__ = 'chat_model'
    __table_args__ = {
        'comment': '模型表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci',
        'mysql_engine': 'InnoDB'
    }
    id = Column(String(32), primary_key=True, comment='主键')
    type = Column(String(255), nullable=True, comment='大模型类型，ollama本地大模型/deepseek/tongyi在线大模型')
    api_key = Column(String(255), nullable=True, comment='在线大模型的api_key,ollama本地大模型则为空')
    model_name = Column(String(255), nullable=True, comment='模型名称')
    base_url = Column(String(500), nullable=True, comment='API基础URL')
    disabled = Column(Integer, default=0, comment='是否禁用：0启用，1禁用')
    create_time = Column(DateTime, nullable=True, comment='创建时间')
    update_time = Column(DateTime, nullable=True, comment='更新时间')