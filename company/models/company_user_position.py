# company/models/company_user_position.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func, UniqueConstraint
from common.config.common_database import Base


class CompanyUserPosition(Base):
    """用户职位关联表（用于关联用户和职位）"""
    __tablename__ = 'company_user_position'
    __table_args__ = (
        UniqueConstraint('user_id', 'position_id', name='uk_user_position'),
        {
            'comment': '用户职位关联表',
            'mysql_charset': 'utf8mb4',
            'mysql_collate': 'utf8mb4_unicode_ci'
        }
    )

    id = Column(String(32), primary_key=True, comment='主键ID')
    user_id = Column(String(32), nullable=False, comment='用户ID')
    position_id = Column(String(32), nullable=False, comment='职位ID')
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment='更新时间')