from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class LogSchema(BaseModel):
    """日志Schema"""
    id: str
    request_id: str
    user_id: Optional[str] = None
    path: str
    method: str
    query_params: Optional[str] = None
    request_body: Optional[str] = None
    request_headers: Optional[str] = None
    client_ip: Optional[str] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[str] = None
    execute_time: Optional[int] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class AsyncLogData(BaseModel):
    """异步日志数据"""
    id: str
    request_id: str
    user_id: Optional[str] = None
    path: str
    method: str
    query_params: Optional[str] = None
    request_body: Optional[str] = None
    request_headers: Optional[str] = None
    client_ip: Optional[str] = None
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[str] = None
    execute_time: Optional[int] = None
    error_message: Optional[str] = None