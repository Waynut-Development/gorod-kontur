from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from dotenv import load_dotenv

from .database import engine, Base
from . import schemas, crud, services
from .telegram_bot import init_bot

# Загрузка переменных окружения
load_dotenv()

# Создание таблиц БД
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Городской Контур API",
    description="API для платформы гражданских инициатив",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключение роутеров напрямую
from .api.endpoints import ideas, users, analytics, telegram
app.include_router(ideas.router, prefix="/api", tags=["ideas"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(telegram.router, prefix="/telegram", tags=["telegram"])

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "gorod-kontur-api",
        "version": "2.0.0",
        "database": "connected"
    }

@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        init_bot(telegram_token)
        print("✅ Telegram бот инициализирован")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN не установлен")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)