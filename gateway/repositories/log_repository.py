import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from fastapi.logger import logger

from gateway.models.log_model import LogModel
from gateway.schemas.log_schema import LogSchema, AsyncLogData


class LogRepository:
    """日志数据仓库"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_log(self, log_data: AsyncLogData) -> Optional[LogSchema]:
        """创建日志记录"""
        try:
            db_log = LogModel(
                id=log_data.id,
                request_id=log_data.request_id,
                user_id=log_data.user_id,
                path=log_data.path,
                method=log_data.method,
                query_params=log_data.query_params,
                request_body=log_data.request_body,
                request_headers=log_data.request_headers,
                client_ip=log_data.client_ip,
                response_status=log_data.response_status,
                response_body=log_data.response_body,
                response_headers=log_data.response_headers,
                execute_time=log_data.execute_time,
                error_message=log_data.error_message
            )
            
            self.db.add(db_log)
            self.db.commit()
            
            return LogSchema.model_validate(db_log)
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"保存日志失败: {str(e)}", exc_info=True)
            return None
    
    def batch_create_logs(self, logs_data: list[AsyncLogData]) -> int:
        """批量创建日志记录"""
        success_count = 0
        try:
            for log_data in logs_data:
                db_log = LogModel(
                    id=log_data.id,
                    request_id=log_data.request_id,
                    user_id=log_data.user_id,
                    path=log_data.path,
                    method=log_data.method,
                    query_params=log_data.query_params,
                    request_body=log_data.request_body,
                    request_headers=log_data.request_headers,
                    client_ip=log_data.client_ip,
                    response_status=log_data.response_status,
                    response_body=log_data.response_body,
                    response_headers=log_data.response_headers,
                    execute_time=log_data.execute_time,
                    error_message=log_data.error_message
                )
                self.db.add(db_log)
                success_count += 1
            
            self.db.commit()
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"批量保存日志失败: {str(e)}", exc_info=True)
        
        return success_count