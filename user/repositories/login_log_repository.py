from sqlalchemy.orm import Session
from user.models.login_log_model import LoginLogModel


class LoginLogRepository:
    """登录日志数据仓库"""

    def __init__(self, db: Session):
        self.db = db
    def create(self, user_id, ip, login_type) -> LoginLogModel:
        db_log = LoginLogModel(
            user_id=user_id,
            ip=ip,
            login_type=login_type
        )
        self.db.add(db_log)
        self.db.commit()
        return db_log
