from fastapi import FastAPI
from chat.routers import router as chat_router
from chat.config import settings
import os

app = FastAPI(title="AI Chat Service")
app.include_router(chat_router)

@app.on_event("startup")
async def startup():
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)