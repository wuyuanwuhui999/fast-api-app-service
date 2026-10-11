from sqlalchemy import Column, DateTime, Integer

from common.config.common_database import Base


class MusicCategoryRelationModel(Base):
    """歌曲分类表（music_category_relation）：分类与歌曲的关联"""
    __tablename__ = "music_category_relation"
    __table_args__ = {
        "comment": "歌曲分类表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    music_id = Column(Integer, nullable=True, comment="音乐id")
    category_id = Column(Integer, nullable=True, comment="类型id")
    create_time = Column(DateTime, nullable=True, comment="创建时间")
    update_time = Column(DateTime, nullable=True, comment="更新时间")

    def __repr__(self):
        return f"<MusicCategoryRelation(id={self.id}, music_id={self.music_id}, category_id={self.category_id})>"
