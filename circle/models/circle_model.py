# circle/models/circle_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from common.config.common_database import Base


class Circle(Base):
    """朋友圈（电影圈/音乐圈）表"""
    __tablename__ = "circle"
    __table_args__ = {
        "comment": "朋友圈表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    relation_id = Column(Integer, nullable=True, comment="关联音乐audio_id或电影movie_id")
    content = Column(String(3000), nullable=True, comment="朋友圈内容")
    imgs = Column(String(1000), nullable=True, comment="朋友圈图片，多张用逗号隔开")
    type = Column(String(255), nullable=True, comment="类型（MUSIC/MOVIE）")
    user_id = Column(String(32), nullable=True, comment="用户id")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")
    permission = Column(Integer, nullable=True, comment="权限，0不公开，1公开")

    def __repr__(self):
        return f"<Circle(id={self.id}, type={self.type}, user_id={self.user_id})>"
