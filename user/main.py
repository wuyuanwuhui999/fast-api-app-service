from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from user.routers import user
from user.database import engine, Base
from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings  # 不是 from pydantic import BaseSettings

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


load_dotenv()  # 加载 .env 文件

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)