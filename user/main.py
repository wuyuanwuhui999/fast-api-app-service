from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.routers import user_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.router)

@app.get("/")
async def root():
    return {"message": "User Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "user"}


def create_app():
    """创建应用（用于Nacos注册）"""
    return app


# 注册到Nacos的装饰器
@service_registry.register(
    service_name="user-service",
    port=4005,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4005)