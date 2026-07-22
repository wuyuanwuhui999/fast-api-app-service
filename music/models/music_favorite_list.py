# music/models/music_favorite_list.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, Index, UniqueConstraint
from common.config.common_database import Base


class MusicFavoriteListModel(Base):
    """音乐收藏夹列表表（收藏夹与音乐的关联表）"""
    __tablename__ = "music_favorite_list"
    __table_args__ = (
        Index("idx_favorite_id", "favorite_id"),
        Index("idx_music_id", "music_id"),
        UniqueConstraint("favorite_id", "music_id", name="uk_favorite_music"),
        {
            "comment": "音乐收藏夹列表表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci"
        }
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    favorite_id = Column(Integer, nullable=False, comment="收藏夹ID")
    music_id = Column(Integer, nullable=False, comment="音乐ID")
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MusicFavoriteList(id={self.id}, favorite_id={self.favorite_id}, music_id={self.music_id})>"