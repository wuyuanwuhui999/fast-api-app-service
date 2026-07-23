# social/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from social.routers import social_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Social Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(social_router.router)


@app.get("/")
async def root():
    return {"message": "Social Service is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "social"}


def create_app():
    """创建应用（用于Nacos注册）"""
    return app


# 注册到Nacos
@service_registry.register(
    service_name="social-service",
    port=4003,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4003)