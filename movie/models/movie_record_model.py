# movie/models/movie_record_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from common.config.common_database import Base


class MoviePlayRecordModel(Base):
    """电影播放记录表"""
    __tablename__ = "movie_play_record"
    __table_args__ = {"comment": "电影播放记录表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    movie_id = Column(Integer, nullable=False, comment="电影ID")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MoviePlayRecord(id={self.id}, movie_id={self.movie_id})>"


class MovieViewRecordModel(Base):
    """电影浏览记录表"""
    __tablename__ = "movie_view_record"
    __table_args__ = {"comment": "电影浏览记录表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    movie_id = Column(Integer, nullable=False, comment="电影ID")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MovieViewRecord(id={self.id}, movie_id={self.movie_id})>"


class MovieFavoriteModel(Base):
    """电影收藏表"""
    __tablename__ = "movie_favorite"
    __table_args__ = {"comment": "电影收藏表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    movie_id = Column(Integer, nullable=False, comment="电影ID")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MovieFavorite(id={self.id}, movie_id={self.movie_id})>"
