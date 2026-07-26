# movie/models/search_history_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, func
from common.config.common_database import Base


class SearchHistoryModel(Base):
    """搜索历史表"""
    __tablename__ = "search_history"
    __table_args__ = {"comment": "搜索历史表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    type = Column(String(255), nullable=True, comment="搜索类型")
    keyword = Column(String(255), nullable=True, comment="搜索关键词")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, keyword={self.keyword})>"
