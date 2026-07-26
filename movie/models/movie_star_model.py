# movie/models/movie_star_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from common.config.common_database import Base


class MovieStarModel(Base):
    """电影演员表"""
    __tablename__ = "movie_stars"
    __table_args__ = {"comment": "电影演员表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    star_name = Column(String(255), nullable=True, comment="演员名称")
    img = Column(String(1000), nullable=True, comment="演员图片地址")
    local_img = Column(String(1000), nullable=True, comment="本地图片")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")
    movie_id = Column(String(255), nullable=True, comment="电影id")
    role = Column(String(255), nullable=True, comment="角色")
    href = Column(String(1000), nullable=True, comment="演员的豆瓣链接地址")
    works = Column(String(1000), nullable=True, comment="代表作")

    def __repr__(self):
        return f"<MovieStar(id={self.id}, star_name={self.star_name})>"
