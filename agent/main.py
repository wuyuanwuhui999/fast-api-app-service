# agent/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from agent.routers import agent_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

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
    port=3010,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=3010)