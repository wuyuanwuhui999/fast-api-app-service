from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prompt.routers import prompt_router
from common.config.common_database import engine, Base
from common.utils.service_registry import service_registry

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Prompt Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prompt_router.router)

@app.get("/")
async def root():
    return {"message": "Prompt Service is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "prompt"}


def create_app():
    return app


@service_registry.register(
    service_name="prompt-service",
    port=4008,
    ip="0.0.0.0"
)
def start_app():
    return app


if __name__ == "__main__":
    import uvicorn
    start_app()
    uvicorn.run(app, host="0.0.0.0", port=4008)