from sqlalchemy import Column, String, Integer, Text, DateTime, BigInteger, func
from common.config.common_database import Base


class LogModel(Base):
    """网关请求日志模型"""
    __tablename__ = 'log'
    __table_args__ = {
        'comment': '网关请求日志表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_0900_ai_ci'
    }

    id = Column(String(32), primary_key=True, comment='主键ID')
    request_id = Column(String(64), nullable=False, comment='请求唯一ID')
    user_id = Column(String(50), nullable=True, comment='用户ID')
    path = Column(String(500), nullable=False, comment='请求路径')
    method = Column(String(10), nullable=False, comment='HTTP方法')
    query_params = Column(Text, nullable=True, comment='查询参数')
    request_body = Column(Text, nullable=True, comment='请求体')
    request_headers = Column(Text, nullable=True, comment='请求头')
    client_ip = Column(String(50), nullable=True, comment='客户端IP')
    response_status = Column(Integer, nullable=True, comment='响应状态码')
    response_body = Column(Text, nullable=True, comment='响应体')
    response_headers = Column(Text, nullable=True, comment='响应头')
    execute_time = Column(BigInteger, nullable=True, comment='执行时间(毫秒)')
    create_time = Column(DateTime, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment='更新时间')
    error_message = Column(Text, nullable=True, comment='错误信息')