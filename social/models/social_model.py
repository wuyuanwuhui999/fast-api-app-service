# social/models/social_model.py
from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Index, text
from common.config.common_database import Base


class SocialComment(Base):
    """评论表"""
    __tablename__ = "social_comment"
    __table_args__ = (
        Index("idx_relation_type", "relation_id", "type"),
        Index("idx_top_id", "top_id"),
        Index("idx_parent_id", "parent_id"),
        Index("idx_user_id", "user_id"),
        {
            "comment": "社交评论表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    content = Column(String(500), nullable=False, comment="评论内容")
    parent_id = Column(BigInteger, nullable=True, comment="父评论ID，一级评论为NULL")
    top_id = Column(BigInteger, nullable=True, comment="顶级评论ID，用于快速查询回复")
    relation_id = Column(BigInteger, nullable=False, comment="关联资源ID")
    type = Column(String(50), nullable=False, comment="资源类型（movie/article/music等）")
    user_id = Column(String(32), nullable=False, comment="评论用户ID")
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    update_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间")

    def __repr__(self):
        return f"<SocialComment(id={self.id}, content={self.content[:20]})>"


class SocialLike(Base):
    """点赞/收藏表"""
    __tablename__ = "social_like"
    __table_args__ = (
        Index("idx_relation_type", "relation_id", "type"),
        Index("idx_user_relation", "user_id", "relation_id", "type", unique=True),
        {
            "comment": "社交点赞/收藏表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    relation_id = Column(BigInteger, nullable=False, comment="关联资源ID")
    type = Column(String(50), nullable=False, comment="资源类型（movie/article/music等）")
    user_id = Column(String(32), nullable=False, comment="用户ID")
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment="创建时间")
    update_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment="更新时间")

    def __repr__(self):
        return f"<SocialLike(id={self.id}, relation_id={self.relation_id}, user_id={self.user_id})>"