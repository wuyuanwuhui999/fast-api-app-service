from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import get_settings

settings = get_settings()

# 创建数据库连接URL
SQLALCHEMY_DATABASE_URL = settings.database_url

# 创建数据库引擎
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    connect_args={"charset": "utf8mb4"}  # 添加MySQL专用字符集配置
)

# 每个请求独立的会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

# 依赖注入用的数据库会话
def get_db():
    """
    获取数据库会话的依赖函数
    使用示例:
    def some_route(db: Session = Depends(get_db)):
        # 使用db操作数据库
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()