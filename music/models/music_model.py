# music/models/music_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, func
from common.config.common_database import Base


class MusicModel(Base):
    """音乐主表"""
    __tablename__ = "music"
    __table_args__ = {
        "comment": "音乐主表",
        "mysql_charset": "utf8mb4",
        "mysql_collate": "utf8mb4_general_ci"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    album_id = Column(Integer, nullable=True, comment="专辑id")
    song_name = Column(String(1000), nullable=True, comment="歌曲名称")
    author_id = Column(Integer, nullable=True, comment="歌手id")
    author_name = Column(String(255), nullable=True, comment="作者名称")
    album_name = Column(String(255), nullable=True, comment="专辑名称")
    version = Column(String(255), nullable=True, comment="版本")
    language = Column(String(255), nullable=True, comment="语言")
    publish_date = Column(DateTime, nullable=True, comment="发布日期")
    wide_audio_id = Column(Integer, nullable=True, comment="宽度音频id")
    is_publish = Column(Integer, nullable=True, comment="是否发布")
    big_pack_id = Column(Integer, nullable=True, comment="大型集合id")
    final_id = Column(Integer, nullable=True, comment="最终id")
    audio_id = Column(Integer, nullable=True, comment="音频id")
    similar_audio_id = Column(Integer, nullable=True, comment="相似的音乐id")
    is_hot = Column(Integer, nullable=True, comment="是否热门")
    album_audio_id = Column(Integer, nullable=True, comment="歌曲音频id")
    audio_group_id = Column(Integer, nullable=True, comment="专辑id")
    cover = Column(String(255), nullable=True, comment="歌曲图片")
    play_url = Column(String(255), nullable=True, comment="网络播放地址")
    local_play_url = Column(String(255), nullable=True, comment="本地播放地址")
    source_name = Column(String(255), nullable=True, comment="播放源")
    source_url = Column(String(1000), nullable=True, comment="播放地址")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")
    label = Column(String(255), nullable=True, comment="标签")
    lyrics = Column(Text, nullable=True, comment="歌词")
    permission = Column(Integer, nullable=True, comment="播放权限")

    def __repr__(self):
        return f"<Music(id={self.id}, song_name={self.song_name})>"


class MusicLikeModel(Base):
    """音乐点赞表"""
    __tablename__ = "music_like"
    __table_args__ = {
        "comment": "音乐点赞表",
        "mysql_charset": "utf8mb3"
    }

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    music_id = Column(Integer, nullable=False, comment="音乐ID")
    user_id = Column(String(255), nullable=True, comment="用户ID")
    create_time = Column(DateTime, nullable=True, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, nullable=True, onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<MusicLike(id={self.id}, music_id={self.music_id}, user_id={self.user_id})>"