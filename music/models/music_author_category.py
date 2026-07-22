from sqlalchemy import Column, Integer, String, DateTime, SmallInteger, func
from common.config.common_database import Base


class MusicAuthorCategoryModel(Base):
    """歌手分类表"""
    __tablename__ = "music_author_category"
    __table_args__ = {
        "comment": "歌手分类表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    category_name = Column(String(100), nullable=False, comment="分类名称")
    rank = Column(Integer, nullable=True, default=0, comment="排序权重，数值越大越靠前")
    disabled = Column(SmallInteger, nullable=True, default=0, comment="是否禁用：0-启用，1-禁用")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MusicAuthorCategory(id={self.id}, category_name={self.category_name})>"