from fastapi import FastAPI
from chat.routers.routes import router as chat_router
from chat.config.config import settings

app = FastAPI(title="AI Chat Service")
app.include_router(chat_router)

@app.on_event("startup")
async def startup():
    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)