from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tenant.routers import tenants_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Tenant Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tenants_router.router)

@app.get("/")
async def root():
    return {"message": "Tenant Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "tenant"}


def create_app():
    return app


@service_registry.register(
    service_name="tenant-service",
    port=4007,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4007)