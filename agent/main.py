from fastapi import FastAPI, WebSocket  # 添加 WebSocket 导入
from fastapi.middleware.cors import CORSMiddleware
from agent.routers import agent_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

import logging
import os
import sys

# ---- 日志：让 agent 模块自身的 INFO 日志（含 LLM 请求参数/提示词/工具调用）输出到控制台 ----
# uvicorn 默认只给 uvicorn.* logger 配 handler，业务 logger.info 会被丢弃；
# 这里只给 "agent" 这一个 logger 挂 stdout handler，不影响其他模块和 uvicorn 日志。
_AGENT_LEVEL = os.getenv("AGENT_LOG_LEVEL", "INFO").upper()
_agent_logger = logging.getLogger("agent")
if not _agent_logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    ))
    _agent_logger.addHandler(_handler)
_agent_logger.setLevel(getattr(logging, _AGENT_LEVEL, logging.INFO))
_agent_logger.propagate = False

# 可选：AGENT_LLM_LOG_DEBUG=1 时打开 langchain 原生 debug（打印最原始的 prompt/响应）
if os.getenv("AGENT_LLM_LOG_DEBUG", "0") in ("1", "true", "True"):
    try:
        from langchain_core.globals import set_debug, set_verbose
        set_debug(True)
        set_verbose(True)
        _agent_logger.info("[AgentService] 已开启 langchain debug/verbose（AGENT_LLM_LOG_DEBUG=1）")
    except Exception as e:  # pragma: no cover
        _agent_logger.warning(f"[AgentService] 开启 langchain debug 失败: {e}")

# 创建数据库表（如果 agent 模块有独立模型，否则可以省略）
# Base.metadata.create_all(bind=engine)

app = FastAPI(title="Agent Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_router.router)


@app.get("/")
async def root():
    return {"message": "Agent Service is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "agent"}


def create_app():
    """创建应用（用于Nacos注册）"""
    return app


# 注册到Nacos
@service_registry.register(
    service_name="agent-service",
    port=4010,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4010)