from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.routers import user
from common.config.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="User Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)

@app.get("/")
async def root():
    return {"message": "User Service is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)