# movie/models/movie_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Double, func
from common.config.common_database import Base


class MovieModel(Base):
    """电影主表（对应 movie 和 movie_network 表）"""
    __tablename__ = "movie"
    __table_args__ = {
        "comment": "电影主表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    movie_id = Column(Integer, nullable=True, comment="电影id")
    director = Column(String(255), nullable=True, comment="导演")
    star = Column(String(1000), nullable=True, comment="主演")
    type = Column(String(255), nullable=True, comment="类型")
    country_language = Column(String(255), nullable=True, comment="国家/语言")
    viewing_state = Column(String(255), nullable=True, comment="观看状态")
    release_time = Column(String(255), nullable=True, comment="上映时间")
    plot = Column(Text, nullable=True, comment="剧情")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")
    movie_name = Column(String(255), nullable=True, comment="电影名称")
    is_recommend = Column(String(255), nullable=True, comment="是否推荐，0:不推荐，1:推荐")
    img = Column(String(1000), nullable=True, comment="电影海报")
    classify = Column(String(255), nullable=True, comment="分类：电影,电视剧,动漫,综艺,新片库等")
    source_name = Column(String(255), nullable=True, comment="来源名称")
    source_url = Column(String(1000), nullable=True, comment="来源地址")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    local_img = Column(String(1000), nullable=True, comment="本地图片")
    label = Column(String(255), nullable=True, comment="播放集数/标签")
    original_href = Column(String(1000), nullable=True, comment="源地址")
    description = Column(String(1000), nullable=True, comment="简单描述")
    target_href = Column(String(1000), nullable=True, comment="链接地址")
    use_status = Column(String(255), nullable=True, comment="使用状态，0未使用，1使用中")
    score = Column(Double, nullable=True, comment="评分")
    category = Column(String(255), nullable=True, comment="类目：banner首屏，carousel滚动轮播")
    ranks = Column(String(255), nullable=True, comment="排名")
    user_id = Column(String(255), nullable=True, comment="用户名")
    douban_url = Column(String(1000), nullable=True, comment="豆瓣网url")
    duration = Column(Integer, default=0, comment="播放时长")
    privilege_id = Column(Integer, default=0, comment="观看权限")

    def __repr__(self):
        return f"<Movie(id={self.id}, movie_name={self.movie_name})>"


class MovieCategoryModel(Base):
    """电影分类表"""
    __tablename__ = "movie_category"
    __table_args__ = {"comment": "电影分类表", "mysql_charset": "utf8mb4"}

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    category = Column(String(255), nullable=True, comment="类目")
    classify = Column(String(255), nullable=True, comment="分类")
    page_name = Column(String(255), nullable=True, comment="页面名称")
    status = Column(String(10), nullable=True, comment="状态：1启用")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MovieCategory(id={self.id}, category={self.category})>"
