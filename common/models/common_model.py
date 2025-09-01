from sqlalchemy import Column, String, Integer, DateTime, Boolean
from common.config.common_database import Base
from pydantic import BaseModel


class UserMode(Base):
    __tablename__ = "user"  # 注意表名改为单数形式，与你数据库一致
    __table_args__ = {
        'comment': '用户表',
        'mysql_charset': 'utf8',
        'mysql_collate': 'utf8_general_ci',
        'mysql_engine': 'InnoDB'
    }

    id = Column(String(32), primary_key=True, comment='主键id')
    user_account = Column(String(20), nullable=False, unique=True, index=True, comment='账号')
    password = Column(String(255), nullable=False, comment='密码')
    create_date = Column(DateTime, comment='创建时间')
    update_date = Column(DateTime, comment='更新时间')
    username = Column(String(255), nullable=False, comment='昵称')
    telephone = Column(String(20), comment='电话')
    email = Column(String(255), comment='邮箱')
    avater = Column(String(255), comment='头像地址')  # 注意字段名是avater不是avater
    birthday = Column(String(16), comment='出生年月日')
    sex = Column(String(1), comment='性别，0:男，1:女')  # 原表是varchar(1)
    role = Column(String(255), comment='角色')
    sign = Column(String(255), comment='个性签名')
    region = Column(String(255), comment='地区')
    disabled = Column(Integer, default=0, comment='是否禁用，0表示不不禁用，1表示禁用')
    permission = Column(Integer, default=0, comment='权限大小')


class LoginForm(BaseModel):
    userAccount: str
    password: str
