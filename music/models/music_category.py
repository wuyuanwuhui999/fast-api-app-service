from sqlalchemy import Column, DateTime, Integer, String

from common.config.common_database import Base


class MusicCategoryModel(Base):
    """歌曲分类名称表（music_category）"""
    __tablename__ = "music_category"
    __table_args__ = {
        "comment": "歌曲分类名称表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    img = Column(String(255), nullable=True, comment="类型图片")
    category = Column(String(255), nullable=True, comment="小分类")
    classify = Column(String(255), nullable=True, comment="大分类")
    create_time = Column(DateTime, nullable=True, comment="创建时间")
    update_time = Column(DateTime, nullable=True, comment="更新时间")

    def __repr__(self):
        return f"<MusicCategory(id={self.id}, category={self.category}, classify={self.classify})>"
