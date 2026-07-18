from sqlalchemy import Column, Integer, String, DateTime, func
from common.config.common_database import Base


class MusicAuthorLikeModel(Base):
    """歌手点赞表"""
    __tablename__ = "music_author_like"
    __table_args__ = {
        "comment": "歌手点赞表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    author_id = Column(Integer, nullable=False, comment="歌手ID（关联music_authors表的id）")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MusicAuthorLike(id={self.id}, author_id={self.author_id}, user_id={self.user_id})>"