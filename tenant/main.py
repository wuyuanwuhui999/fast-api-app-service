from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tenant.routers import tenants_router
from common.config.common_database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="tenant Service", version="1.0.0")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4004)