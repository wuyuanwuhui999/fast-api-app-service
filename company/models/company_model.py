# company/models/company_model.py
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, SmallInteger, Text, func
from common.config.common_database import Base


class CompanyModel(Base):
    """企业表"""
    __tablename__ = 'company'
    __table_args__ = {
        'comment': '企业表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }

    id = Column(String(32), primary_key=True, comment='企业ID')
    name = Column(String(100), nullable=False, comment='企业名称')
    code = Column(String(50), nullable=False, unique=True, comment='企业编码')
    description = Column(String(255), comment='企业描述')
    # logo = Column(String(255), comment='企业Logo')  # 暂时注释，数据库表中没有此字段
    status = Column(SmallInteger, default=1, comment='状态：0-禁用，1-启用')
    create_date = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_date = Column(DateTime, onupdate=datetime.now, comment='更新时间')
    created_by = Column(String(32), nullable=False, comment='创建人ID')
    updated_by = Column(String(32), comment='更新人ID')


class CompanyUserModel(Base):
    """企业用户关联表"""
    __tablename__ = 'company_user'
    __table_args__ = {
        'comment': '企业用户关联表',
        'mysql_charset': 'utf8mb4',
        'mysql_collate': 'utf8mb4_general_ci'
    }

    id = Column(String(32), primary_key=True, comment='主键ID')
    company_id = Column(String(32), nullable=False, comment='企业ID')
    user_id = Column(String(32), nullable=False, comment='用户ID')
    role = Column(String(10), nullable=False, default='0', comment='角色：0-普通成员，1-管理员，2-人事，3-企业老板')
    is_default = Column(SmallInteger, default=0, comment='是否默认企业：0-否，1-是')
    join_date = Column(DateTime, nullable=False, default=datetime.now, comment='加入时间')
    status = Column(SmallInteger, default=1, comment='状态：0-已移除，1-正常')
    create_by = Column(String(32), nullable=False, comment='创建人ID')
    create_date = Column(DateTime, nullable=False, default=datetime.now, comment='创建时间')
    update_by = Column(String(32), comment='更新人ID')
    update_date = Column(DateTime, onupdate=datetime.now, comment='更新时间')


# 导出Base供main.py使用
Base = Base