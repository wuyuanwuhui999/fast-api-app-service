from sqlalchemy import Column, Integer, String, DateTime
from common.config.common_database import Base


class MusicClassifyRelationModel(Base):
    """音乐分类关联表"""
    __tablename__ = "music_classify_relation"
    __table_args__ = {
        "comment": "音乐分类关联表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    classify_name = Column(String(255), nullable=True, comment="标签")
    permission = Column(Integer, nullable=True, comment="权限")
    classify_rank = Column(Integer, nullable=True, comment="分类排序，数值越大越靠前")
    cover = Column(String(255), nullable=True, comment="图标")
    disabled = Column(Integer, nullable=True, comment="是否启用")
    create_time = Column(DateTime, nullable=True, comment="创建时间")
    update_time = Column(DateTime, nullable=True, comment="更新时间")

    def __repr__(self):
        return f"<MusicClassifyRelation(id={self.id}, classify_name={self.classify_name})>"