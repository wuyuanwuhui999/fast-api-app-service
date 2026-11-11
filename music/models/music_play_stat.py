from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Index
from sqlalchemy.dialects.mysql import INTEGER, BIGINT
from common.config.common_database import Base


class UserMusicPlayStatModel(Base):
    """用户播放记录统计表（每用户每首歌的播放次数，music_record 的汇总）

    主键 (user_id, music_id)：播放记录插入后异步 UPSERT 自增，读"我听了几次"直接命中聚簇索引。
    """
    __tablename__ = "music_user_play_stat"
    __table_args__ = (
        Index("idx_user_last", "user_id", "last_play_time"),
        {
            "comment": "用户播放记录统计表（每用户每首歌的播放次数，music_record 的汇总）",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "mysql_engine": "InnoDB"
        }
    )

    user_id = Column(String(64), primary_key=True, comment="用户id")
    music_id = Column(Integer, primary_key=True, comment="音乐id")
    play_count = Column(INTEGER(unsigned=True), nullable=False, default=0, comment="该用户播放该歌曲的总次数")
    first_play_time = Column(DateTime, nullable=True, comment="首次播放时间")
    last_play_time = Column(DateTime, nullable=True, comment="最近播放时间")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    update_time = Column(DateTime, nullable=False, comment="更新时间")

    def __repr__(self):
        return f"<UserMusicPlayStat(user_id={self.user_id}, music_id={self.music_id}, play_count={self.play_count})>"


class MusicPlayStatModel(Base):
    """歌曲播放记录统计表（每首歌的播放总次数，用于搜索排名/排行榜）"""
    __tablename__ = "music_play_stat"
    __table_args__ = (
        Index("idx_play_count", "play_count"),
        {
            "comment": "歌曲播放记录统计表（每首歌的播放总次数，用于搜索/排行榜）",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_general_ci",
            "mysql_engine": "InnoDB"
        }
    )

    music_id = Column(Integer, primary_key=True, comment="音乐id")
    play_count = Column(BIGINT(unsigned=True), nullable=False, default=0, comment="该歌曲的播放总次数")
    first_play_time = Column(DateTime, nullable=True, comment="首次播放时间")
    last_play_time = Column(DateTime, nullable=True, comment="最近播放时间")
    create_time = Column(DateTime, nullable=False, comment="创建时间")
    update_time = Column(DateTime, nullable=False, comment="更新时间")

    def __repr__(self):
        return f"<MusicPlayStat(music_id={self.music_id}, play_count={self.play_count})>"
