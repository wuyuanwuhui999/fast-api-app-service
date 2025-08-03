from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chat.routers import router
from common.config.database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="chat Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/")
async def root():
    return {"message": "Chat Service is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)