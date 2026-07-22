# music/models/music_favorite_directory.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, Index
from common.config.common_database import Base


class MusicFavoriteDirectoryModel(Base):
    """音乐收藏夹目录表"""
    __tablename__ = "music_favorite_directory"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        {
            "comment": "音乐收藏夹目录表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci"
        }
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(String(32), nullable=False, comment="用户ID")
    name = Column(String(100), nullable=False, comment="收藏夹名称")
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MusicFavoriteDirectory(id={self.id}, name={self.name})>"