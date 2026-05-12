import asyncio
import threading
import queue
import uuid
import time
from typing import Optional
from fastapi import Request, Response
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import SessionLocal
from gateway.repositories.log_repository import LogRepository
from gateway.schemas.log_schema import AsyncLogData


class AsyncLogWriter:
    """异步日志写入器 - 使用后台线程+队列"""
    
    _instance = None
    _queue: queue.Queue
    _thread: threading.Thread
    _running: bool
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化队列和后台线程"""
        self._queue = queue.Queue(maxsize=10000)  # 最大队列长度
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        logger.info("异步日志写入器已启动")
    
    def _worker(self):
        """后台工作线程，批量写入日志"""
        batch_size = 10
        batch_timeout = 1.0  # 秒
        
        while self._running:
            batch = []
            start_time = time.time()
            
            try:
                # 获取第一条日志（阻塞最多1秒）
                try:
                    item = self._queue.get(timeout=batch_timeout)
                    batch.append(item)
                except queue.Empty:
                    continue
                
                # 继续获取更多日志，直到达到批量大小或超时
                while len(batch) < batch_size:
                    try:
                        item = self._queue.get(timeout=0.1)
                        batch.append(item)
                    except queue.Empty:
                        break
                
                # 批量写入数据库
                if batch:
                    self._write_batch(batch)
                    
            except Exception as e:
                logger.error(f"异步日志写入失败: {str(e)}", exc_info=True)
    
    def _write_batch(self, batch: list):
        """批量写入数据库"""
        db = SessionLocal()
        try:
            repo = LogRepository(db)
            success_count = repo.batch_create_logs(batch)
            if success_count < len(batch):
                logger.warning(f"批量日志写入部分失败: {success_count}/{len(batch)}")
        except Exception as e:
            logger.error(f"批量写入日志时发生错误: {str(e)}", exc_info=True)
        finally:
            db.close()
    
    def add_log(self, log_data: AsyncLogData):
        """添加日志到队列"""
        try:
            # 非阻塞放入队列
            self._queue.put_nowait(log_data)
        except queue.Full:
            logger.warning("日志队列已满，丢弃一条日志")
    
    def stop(self):
        """停止日志写入器"""
        self._running = False
        self._thread.join(timeout=5)
        logger.info("异步日志写入器已停止")


class LogService:
    """日志服务"""
    
    def __init__(self):
        self.async_writer = AsyncLogWriter()
    
    async def save_request_log(
        self,
        request: Request,
        response: Response,
        user_id: Optional[str],
        execute_time: int,
        error_message: Optional[str] = None
    ):
        """保存请求日志（异步）"""
        try:
            # 生成请求ID
            request_id = request.headers.get("X-Request-ID")
            if not request_id:
                request_id = str(uuid.uuid4()).replace("-", "")
            
            # 获取请求体
            request_body = None
            try:
                body = await request.body()
                if body:
                    request_body = body.decode('utf-8', errors='ignore')[:65535]  # 限制长度
            except Exception:
                pass
            
            # 获取响应体
            response_body = None
            if hasattr(response, "body"):
                try:
                    if response.body:
                        response_body = response.body.decode('utf-8', errors='ignore')[:65535]
                except Exception:
                    pass
            
            # 构造日志数据
            log_data = AsyncLogData(
                id=str(uuid.uuid4()).replace("-", ""),
                request_id=request_id,
                user_id=user_id,
                path=request.url.path,
                method=request.method,
                query_params=str(request.query_params) if request.query_params else None,
                request_body=request_body,
                request_headers=self._headers_to_str(request.headers),
                client_ip=self._get_client_ip(request),
                response_status=response.status_code,
                response_body=response_body,
                response_headers=self._headers_to_str(response.headers),
                execute_time=execute_time,
                error_message=error_message
            )
            
            # 异步写入
            self.async_writer.add_log(log_data)
            
        except Exception as e:
            logger.error(f"保存请求日志失败: {str(e)}", exc_info=True)
    
    def _get_client_ip(self, request: Request) -> Optional[str]:
        """获取客户端真实IP"""
        # 优先从代理头获取
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # 从直接连接获取
        if request.client:
            return request.client.host
        
        return None
    
    def _headers_to_str(self, headers) -> Optional[str]:
        """将请求头转换为字符串"""
        try:
            # 过滤掉敏感信息
            sensitive_keys = {"authorization", "cookie", "x-api-key"}
            filtered = {}
            for key, value in headers.items():
                if key.lower() not in sensitive_keys:
                    filtered[key] = value
                else:
                    filtered[key] = "***"
            return str(filtered)
        except Exception:
            return None


# 全局日志服务实例
log_service = LogService()