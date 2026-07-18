from sqlalchemy import Column, Integer, String, DateTime
from common.config.common_database import Base


class MusicAuthorModel(Base):
    """歌手表"""
    __tablename__ = "music_authors"
    __table_args__ = {
        "comment": "歌手表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    author_id = Column(Integer, nullable=True, comment="歌手id")
    author_name = Column(String(255), nullable=True, comment="歌手名称")
    category_id = Column(Integer, nullable=True, comment="分类id")
    is_publish = Column(Integer, nullable=True, comment="是否发布")
    avatar = Column(String(255), nullable=True, comment="头像")
    type = Column(Integer, nullable=True, comment="类型")
    country = Column(String(255), nullable=True, comment="国家")
    birthday = Column(String(255), nullable=True, comment="生日")
    identity = Column(Integer, nullable=True, comment="身份")
    rank = Column(Integer, nullable=True, comment="歌手排名")
    create_time = Column(DateTime, nullable=True, comment="创建时间")
    update_time = Column(DateTime, nullable=True, comment="修改时间")

    def __repr__(self):
        return f"<MusicAuthor(id={self.id}, author_name={self.author_name})>"