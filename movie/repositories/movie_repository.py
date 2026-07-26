# movie/repositories/movie_repository.py
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import func, and_, or_, text, case
from sqlalchemy.orm import Session
from fastapi.logger import logger

from movie.models.movie_model import MovieModel, MovieCategoryModel
from movie.models.movie_star_model import MovieStarModel
from movie.models.movie_url_model import MovieUrlModel
from movie.models.movie_record_model import MoviePlayRecordModel, MovieViewRecordModel, MovieFavoriteModel
from movie.models.search_history_model import SearchHistoryModel


class MovieRepository:
    """电影数据访问层"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 分类相关 ====================

    def find_classify(self) -> List[Dict[str, str]]:
        """查询所有电影分类"""
        try:
            results = (
                self.db.query(MovieModel.classify)
                .group_by(MovieModel.classify)
                .all()
            )
            return [{"classify": row[0]} for row in results if row[0]]
        except Exception as e:
            logger.error(f"查询电影分类失败: {str(e)}", exc_info=True)
            return []

    def get_keyword(self, classify: str) -> Optional[Dict[str, Any]]:
        """获取推荐的关键词电影"""
        try:
            movie = (
                self.db.query(MovieModel)
                .filter(
                    MovieModel.is_recommend == '1',
                    MovieModel.classify == classify
                )
                .order_by(MovieModel.create_time.desc())
                .first()
            )
            if not movie:
                return None
            return self._movie_to_dict(movie)
        except Exception as e:
            logger.error(f"获取推荐电影失败: {str(e)}", exc_info=True)
            return None

    def get_user_msg(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户使用天数和各记录数"""
        try:
            from sqlalchemy import select, text
            sql = text("""
                SELECT CAST(u.userAge as char) AS userAge,
                       CAST(r.viewRecordCount AS char) AS viewRecordCount,
                       CAST(p.playRecordCount AS char) AS playRecordCount,
                       CAST(f.favoriteCount AS char) AS favoriteCount
                FROM (
                    SELECT TIMESTAMPDIFF(DAY, a.create_date, now()) as userAge
                    FROM user a WHERE user_id = :user_id
                ) u,
                (SELECT count(*) as viewRecordCount FROM movie_view_record WHERE user_id = :user_id2) r,
                (SELECT count(*) as playRecordCount FROM movie_play_record WHERE user_id = :user_id3) p,
                (SELECT count(*) as favoriteCount FROM movie_favorite WHERE user_id = :user_id4) f
            """)
            result = self.db.execute(sql, {
                "user_id": user_id, "user_id2": user_id,
                "user_id3": user_id, "user_id4": user_id
            }).first()
            if result:
                return {
                    "userAge": result[0],
                    "viewRecordCount": result[1],
                    "playRecordCount": result[2],
                    "favoriteCount": result[3]
                }
            return None
        except Exception as e:
            logger.error(f"获取用户信息失败: {str(e)}", exc_info=True)
            return None

    # ==================== 分类相关 ====================

    def get_all_category_by_classify(self, classify: str) -> List[Dict[str, str]]:
        """按classify大类查询所有category小类"""
        try:
            results = (
                self.db.query(MovieCategoryModel)
                .filter(
                    MovieCategoryModel.classify == classify,
                    MovieCategoryModel.category != '轮播'
                )
                .order_by(MovieCategoryModel.update_time.asc())
                .all()
            )
            return [{"category": row.category, "classify": row.classify} for row in results]
        except Exception as e:
            logger.error(f"按classify查询category失败: {str(e)}", exc_info=True)
            return []

    def get_all_category_list_by_page_name(self, page_name: str) -> List[Dict[str, str]]:
        """按页面获取要展示的category小类"""
        try:
            results = (
                self.db.query(MovieCategoryModel)
                .filter(
                    MovieCategoryModel.page_name == page_name,
                    MovieCategoryModel.category != '轮播',
                    MovieCategoryModel.status == '1'
                )
                .order_by(MovieCategoryModel.update_time.asc())
                .all()
            )
            return [{"category": row.category, "classify": row.classify} for row in results]
        except Exception as e:
            logger.error(f"按页面查询category失败: {str(e)}", exc_info=True)
            return []

    def get_category_list(self, classify: str, category: str) -> Tuple[List[Dict[str, Any]], int]:
        """获取大类中的小类"""
        try:
            query = self.db.query(MovieModel).filter(
                MovieModel.classify == classify,
                MovieModel.category == category
            )
            total = query.count()
            results = query.all()
            return [self._movie_to_dict(m) for m in results], total
        except Exception as e:
            logger.error(f"获取category列表失败: {str(e)}", exc_info=True)
            return [], 0

    def get_top_movie_list(self, classify: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """根据分类获取前20条数据"""
        try:
            filters = [MovieModel.classify == classify]
            if category:
                filters.append(MovieModel.classify == classify)  # bug compatible: same as original

            results = (
                self.db.query(MovieModel)
                .filter(*filters)
                .order_by(MovieModel.create_time.desc())
                .limit(20)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取Top电影列表失败: {str(e)}", exc_info=True)
            return []

    # ==================== 搜索 ====================

    def search(
        self,
        classify: Optional[str],
        category: Optional[str],
        label: Optional[str],
        star: Optional[str],
        director: Optional[str],
        keyword: Optional[str],
        start: int,
        page_size: int
    ) -> List[Dict[str, Any]]:
        """搜索电影"""
        try:
            filters = [MovieModel.id.isnot(None)]
            if classify:
                filters.append(MovieModel.classify == classify)
            if category:
                filters.append(MovieModel.category == category)
            if label:
                filters.append(MovieModel.label.like(f'%{label}%'))
            if star:
                filters.append(MovieModel.star.like(f'%{star}%'))
            if director:
                filters.append(MovieModel.director.like(f'%{director}%'))
            if keyword:
                keyword_filter = or_(
                    MovieModel.movie_name.like(f'%{keyword}%'),
                    MovieModel.star.like(f'%{keyword}%'),
                    MovieModel.director.like(f'%{keyword}%'),
                    MovieModel.type.like(f'%{keyword}%')
                )
                filters.append(keyword_filter)

            results = (
                self.db.query(MovieModel)
                .filter(*filters)
                .order_by(MovieModel.update_time.desc())
                .offset(start)
                .limit(page_size)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"搜索电影失败: {str(e)}", exc_info=True)
            return []

    def search_total(
        self,
        classify: Optional[str],
        category: Optional[str],
        label: Optional[str],
        star: Optional[str],
        director: Optional[str],
        keyword: Optional[str]
    ) -> int:
        """搜索电影总数"""
        try:
            filters = [MovieModel.id.isnot(None)]
            if classify:
                filters.append(MovieModel.classify == classify)
            if category:
                filters.append(MovieModel.category == category)
            if label:
                filters.append(MovieModel.label.like(f'%{label}%'))
            if star:
                filters.append(MovieModel.star.like(f'%{star}%'))
            if director:
                filters.append(MovieModel.director.like(f'%{director}%'))
            if keyword:
                keyword_filter = or_(
                    MovieModel.movie_name.like(f'%{keyword}%'),
                    MovieModel.star.like(f'%{keyword}%'),
                    MovieModel.director.like(f'%{keyword}%'),
                    MovieModel.type.like(f'%{keyword}%')
                )
                filters.append(keyword_filter)

            return (
                self.db.query(func.count(MovieModel.id))
                .filter(*filters)
                .scalar()
            ) or 0
        except Exception as e:
            logger.error(f"搜索电影总数失败: {str(e)}", exc_info=True)
            return 0

    # ==================== 演员 ====================

    def get_star(self, movie_id: int) -> List[Dict[str, Any]]:
        """获取电影演员列表"""
        try:
            results = (
                self.db.query(MovieStarModel)
                .filter(MovieStarModel.movie_id == str(movie_id))
                .all()
            )
            return [self._star_to_dict(s) for s in results]
        except Exception as e:
            logger.error(f"获取演员列表失败: {str(e)}", exc_info=True)
            return []

    # ==================== 播放地址 ====================

    def get_movie_url(self, movie_id: int) -> List[Dict[str, Any]]:
        """获取电影播放地址"""
        try:
            results = (
                self.db.query(MovieUrlModel)
                .filter(MovieUrlModel.movie_id == movie_id)
                .all()
            )
            return [self._url_to_dict(u) for u in results]
        except Exception as e:
            logger.error(f"获取播放地址失败: {str(e)}", exc_info=True)
            return []

    # ==================== 播放记录 ====================

    def get_play_record(self, user_id: str, start: int, page_size: int) -> List[Dict[str, Any]]:
        """获取播放记录"""
        try:
            results = (
                self.db.query(MovieModel)
                .join(MoviePlayRecordModel, MovieModel.id == MoviePlayRecordModel.movie_id)
                .filter(MoviePlayRecordModel.user_id == user_id)
                .order_by(MoviePlayRecordModel.create_time.desc())
                .offset(start)
                .limit(page_size)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取播放记录失败: {str(e)}", exc_info=True)
            return []

    def save_play_record(self, movie_id: int, user_id: str) -> Optional[int]:
        """保存播放记录（去重）"""
        try:
            existing = (
                self.db.query(MoviePlayRecordModel)
                .filter(
                    MoviePlayRecordModel.movie_id == movie_id,
                    MoviePlayRecordModel.user_id == user_id
                )
                .first()
            )
            if existing:
                return existing.id

            record = MoviePlayRecordModel(
                movie_id=movie_id,
                user_id=user_id,
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            self.db.add(record)
            self.db.commit()
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存播放记录失败: {str(e)}", exc_info=True)
            return None

    # ==================== 浏览记录 ====================

    def get_view_record(self, user_id: str, start: int, page_size: int) -> List[Dict[str, Any]]:
        """获取浏览记录"""
        try:
            results = (
                self.db.query(MovieModel)
                .join(MovieViewRecordModel, MovieModel.id == MovieViewRecordModel.movie_id)
                .filter(MovieViewRecordModel.user_id == user_id)
                .order_by(MovieViewRecordModel.create_time.desc())
                .offset(start)
                .limit(page_size)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取浏览记录失败: {str(e)}", exc_info=True)
            return []

    def save_view_record(self, movie_id: int, user_id: str) -> Optional[int]:
        """保存浏览记录（去重）"""
        try:
            existing = (
                self.db.query(MovieViewRecordModel)
                .filter(
                    MovieViewRecordModel.movie_id == movie_id,
                    MovieViewRecordModel.user_id == user_id
                )
                .first()
            )
            if existing:
                return existing.id

            record = MovieViewRecordModel(
                movie_id=movie_id,
                user_id=user_id,
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            self.db.add(record)
            self.db.commit()
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存浏览记录失败: {str(e)}", exc_info=True)
            return None

    # ==================== 收藏 ====================

    def get_favorite_list(self, user_id: str, start: int, page_size: int) -> List[Dict[str, Any]]:
        """获取收藏列表"""
        try:
            results = (
                self.db.query(MovieModel)
                .join(MovieFavoriteModel, MovieModel.id == MovieFavoriteModel.movie_id)
                .filter(MovieFavoriteModel.user_id == user_id)
                .order_by(MovieFavoriteModel.create_time.desc())
                .offset(start)
                .limit(page_size)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取收藏列表失败: {str(e)}", exc_info=True)
            return []

    def save_favorite(self, movie_id: int, user_id: str) -> Optional[int]:
        """添加收藏（去重）"""
        try:
            existing = (
                self.db.query(MovieFavoriteModel)
                .filter(
                    MovieFavoriteModel.movie_id == movie_id,
                    MovieFavoriteModel.user_id == user_id
                )
                .first()
            )
            if existing:
                return existing.id

            record = MovieFavoriteModel(
                movie_id=movie_id,
                user_id=user_id,
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            self.db.add(record)
            self.db.commit()
            return record.id
        except Exception as e:
            self.db.rollback()
            logger.error(f"添加收藏失败: {str(e)}", exc_info=True)
            return None

    def delete_favorite(self, movie_id: int, user_id: str) -> bool:
        """删除收藏"""
        try:
            deleted = (
                self.db.query(MovieFavoriteModel)
                .filter(
                    MovieFavoriteModel.movie_id == movie_id,
                    MovieFavoriteModel.user_id == user_id
                )
                .delete()
            )
            self.db.commit()
            return deleted > 0
        except Exception as e:
            self.db.rollback()
            logger.error(f"删除收藏失败: {str(e)}", exc_info=True)
            return False

    def is_favorite(self, movie_id: int, user_id: str) -> bool:
        """查询是否已收藏"""
        try:
            count = (
                self.db.query(func.count(MovieFavoriteModel.id))
                .filter(
                    MovieFavoriteModel.movie_id == movie_id,
                    MovieFavoriteModel.user_id == user_id
                )
                .scalar()
            ) or 0
            return count > 0
        except Exception as e:
            logger.error(f"查询收藏状态失败: {str(e)}", exc_info=True)
            return False

    # ==================== 推荐相关 ====================

    def get_your_likes(self, labels: List[str], classify: str) -> List[Dict[str, Any]]:
        """猜你喜欢"""
        try:
            label_filters = [
                MovieModel.label.like(f'%{label.strip()}%')
                for label in labels
            ]
            results = (
                self.db.query(MovieModel)
                .filter(
                    or_(*label_filters),
                    MovieModel.classify == classify
                )
                .order_by(MovieModel.create_time.desc())
                .limit(10)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取猜你喜欢失败: {str(e)}", exc_info=True)
            return []

    def get_recommend(self, classify: str) -> List[Dict[str, Any]]:
        """获取推荐电影"""
        try:
            results = (
                self.db.query(MovieModel)
                .filter(MovieModel.classify == classify)
                .order_by(MovieModel.create_time.desc())
                .limit(20)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"获取推荐电影失败: {str(e)}", exc_info=True)
            return []

    # ==================== 电影详情 ====================

    def get_movie_detail(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """获取电影详情"""
        try:
            movie = (
                self.db.query(MovieModel)
                .filter(MovieModel.movie_id == movie_id)
                .first()
            )
            if not movie:
                return None
            return self._movie_to_dict(movie)
        except Exception as e:
            logger.error(f"获取电影详情失败: {str(e)}", exc_info=True)
            return None

    def get_movie_list_by_type(self, types: List[str], classify: str) -> List[Dict[str, Any]]:
        """按类型获取相似电影"""
        try:
            type_filters = [
                MovieModel.type.like(f'%{t.strip()}%')
                for t in types
            ]
            results = (
                self.db.query(MovieModel)
                .filter(
                    or_(*type_filters),
                    MovieModel.classify == classify
                )
                .order_by(MovieModel.create_time.desc())
                .limit(10)
                .all()
            )
            return [self._movie_to_dict(m) for m in results]
        except Exception as e:
            logger.error(f"按类型获取电影失败: {str(e)}", exc_info=True)
            return []

    # ==================== 搜索历史 ====================

    def get_search_history(self, user_id: str, start: int, page_size: int) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        try:
            results = (
                self.db.query(SearchHistoryModel)
                .filter(
                    SearchHistoryModel.user_id == user_id,
                    SearchHistoryModel.type == '1'
                )
                .order_by(SearchHistoryModel.create_time.desc())
                .offset(start)
                .limit(page_size)
                .all()
            )
            return [self._search_history_to_dict(s) for s in results]
        except Exception as e:
            logger.error(f"获取搜索历史失败: {str(e)}", exc_info=True)
            return []

    def get_search_history_total(self, user_id: str) -> int:
        """获取搜索历史总数"""
        try:
            return (
                self.db.query(func.count(SearchHistoryModel.id))
                .filter(
                    SearchHistoryModel.user_id == user_id,
                    SearchHistoryModel.type == '1'
                )
                .scalar()
            ) or 0
        except Exception as e:
            logger.error(f"获取搜索历史总数失败: {str(e)}", exc_info=True)
            return 0

    # ==================== 工具方法 ====================

    @staticmethod
    def _movie_to_dict(movie: MovieModel) -> Dict[str, Any]:
        """MovieModel 转字典"""
        return {
            "id": movie.id,
            "movie_id": movie.movie_id,
            "director": movie.director,
            "star": movie.star,
            "type": movie.type,
            "country_language": movie.country_language,
            "viewing_state": movie.viewing_state,
            "release_time": movie.release_time,
            "plot": movie.plot,
            "update_time": movie.update_time,
            "movie_name": movie.movie_name,
            "is_recommend": movie.is_recommend,
            "img": movie.img,
            "classify": movie.classify,
            "source_name": movie.source_name,
            "source_url": movie.source_url,
            "create_time": movie.create_time,
            "local_img": movie.local_img,
            "label": movie.label,
            "original_href": movie.original_href,
            "description": movie.description,
            "target_href": movie.target_href,
            "use_status": movie.use_status,
            "score": movie.score,
            "category": movie.category,
            "ranks": movie.ranks,
            "douban_url": movie.douban_url,
            "duration": movie.duration,
            "privilege_id": movie.privilege_id,
        }

    @staticmethod
    def _star_to_dict(star: MovieStarModel) -> Dict[str, Any]:
        return {
            "id": star.id,
            "star_name": star.star_name,
            "img": star.img,
            "local_img": star.local_img,
            "create_time": star.create_time,
            "update_time": star.update_time,
            "movie_id": star.movie_id,
            "role": star.role,
            "href": star.href,
            "works": star.works,
        }

    @staticmethod
    def _url_to_dict(url: MovieUrlModel) -> Dict[str, Any]:
        return {
            "id": url.id,
            "movie_name": url.movie_name,
            "movie_id": url.movie_id,
            "href": url.href,
            "label": url.label,
            "create_time": url.create_time,
            "update_time": url.update_time,
            "url": url.url,
            "play_group": url.play_group,
        }

    @staticmethod
    def _search_history_to_dict(history: SearchHistoryModel) -> Dict[str, Any]:
        return {
            "id": history.id,
            "user_id": history.user_id,
            "type": history.type,
            "keyword": history.keyword,
            "create_time": history.create_time,
        }
