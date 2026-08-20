from sqlalchemy import Column, String, BigInteger, DateTime, func
from common.config.common_database import Base


class LoginLogModel(Base):
    """登录日志表"""
    __tablename__ = 'login_log'
    __table_args__ = {
        'comment': '登录日志表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键ID（自增）')
    user_id = Column(String(50), nullable=True, comment='用户ID')
    ip = Column(String(50), nullable=True, comment='登录IP')
    login_type = Column(String(50), nullable=True, comment='登录类型：login/getUserData')
    create_time = Column(DateTime, server_default=func.now(), comment='登录时间')
