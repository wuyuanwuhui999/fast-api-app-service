from sqlalchemy import Column, String, Integer, DateTime, Boolean
from app.database import Base


class User(Base):
    __tablename__ = "users"  # 注意表名改为复数形式，这是SQLAlchemy的常见实践

    id = Column(String, primary_key=True, index=True)
    user_account = Column(String, unique=True, index=True)
    password = Column(String)
    create_date = Column(DateTime)
    update_date = Column(DateTime)
    username = Column(String)
    telephone = Column(String)
    email = Column(String, unique=True, index=True)
    avatar = Column(String)
    birthday = Column(String)
    sex = Column(Integer)
    sign = Column(String)
    region = Column(String)
    disabled = Column(Boolean, default=False)
    role = Column(String, default="user")
    permission = Column(Integer, default=0)