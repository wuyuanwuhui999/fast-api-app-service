from sqlalchemy import Column, Integer, DateTime
from common.config.common_database import Base


class MusicClassifyModel(Base):
    """音乐分类关联表"""
    __tablename__ = "music_classify"
    __table_args__ = {
        "comment": "音乐分类关联表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    classify_id = Column(Integer, nullable=True, comment="分类ID")
    music_id = Column(Integer, nullable=True, comment="歌曲id")
    audio_rank = Column(Integer, nullable=True, comment="歌曲排名，数值越大越靠前")
    create_time = Column(DateTime, nullable=True, comment="创建时间")
    update_time = Column(DateTime, nullable=True, comment="更新时间")

    def __repr__(self):
        return f"<MusicClassify(id={self.id}, classify_id={self.classify_id}, music_id={self.music_id})>"