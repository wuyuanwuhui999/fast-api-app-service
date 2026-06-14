# company/models/company_position.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from common.config.common_database import Base


class CompanyPosition(Base):
    """企业职位表"""
    __tablename__ = 'company_position'
    __table_args__ = {
        'comment': '企业职位表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }

    id = Column(String(32), primary_key=True, comment='职位ID(UUID)')
    position_name = Column(String(50), nullable=False, comment='职位名称')
    department_id = Column(String(32), nullable=True, comment='所属部门ID')
    description = Column(String(255), nullable=True, comment='职位描述')
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment='创建时间')