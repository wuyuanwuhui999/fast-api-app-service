# music/models/music_record.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func, Index
from common.config.common_database import Base


class MusicRecordModel(Base):
    """音乐播放记录表"""
    __tablename__ = "music_record"
    __table_args__ = (
        Index("idx_user_id", "user_id"),
        Index("idx_music_id", "music_id"),
        Index("idx_user_music_time", "user_id", "music_id", "create_time"),
        {
            "comment": "音乐播放记录表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci"
        }
    )

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(String(32), nullable=False, comment="用户ID")
    music_id = Column(Integer, nullable=False, comment="音乐ID")
    create_time = Column(DateTime, nullable=False, server_default=func.now(), comment="播放时间")

    def __repr__(self):
        return f"<MusicRecord(id={self.id}, user_id={self.user_id}, music_id={self.music_id})>"