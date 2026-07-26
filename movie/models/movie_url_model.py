# movie/models/movie_url_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from common.config.common_database import Base


class MovieUrlModel(Base):
    """电影播放地址表"""
    __tablename__ = "movie_url"
    __table_args__ = {"comment": "电影播放地址表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    movie_name = Column(String(255), nullable=True, comment="电影名称")
    movie_id = Column(Integer, nullable=True, comment="对应电影的id")
    href = Column(String(1000), nullable=True, comment="源地址")
    label = Column(String(255), nullable=True, comment="集数")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")
    url = Column(String(1000), nullable=True, comment="播放地址")
    play_group = Column(String(255), nullable=True, comment="播放分组，1,2")

    def __repr__(self):
        return f"<MovieUrl(id={self.id}, movie_name={self.movie_name})>"
