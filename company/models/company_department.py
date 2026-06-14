# company/models/company_department.py
from datetime import datetime
from sqlalchemy import Column, String, DateTime, func
from common.config.common_database import Base


class CompanyDepartment(Base):
    """企业部门表"""
    __tablename__ = 'company_department'
    __table_args__ = {
        'comment': '企业部门表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_unicode_ci'
    }

    id = Column(String(32), primary_key=True, comment='部门ID(UUID)')
    company_id = Column(String(50), nullable=False, comment='所属企业ID')
    department_name = Column(String(50), nullable=False, comment='部门名称')
    description = Column(String(255), nullable=True, comment='部门描述')
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment='创建时间')