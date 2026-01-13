from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from . import models
from .database import engine
from .api.endpoints import ideas, users, analytics
from .telegram_bot import router as telegram_router, init_bot

# Создание таблиц БД
models.Base.metadata.create_all(bind=engine)

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
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов (фронтенд)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Подключение роутеров
app.include_router(ideas.router)
app.include_router(users.router)
app.include_router(analytics.router)
app.include_router(telegram_router)

@app.on_event("startup")
async def startup_event():
    """Действия при запуске приложения"""
    # Инициализация Telegram бота
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        init_bot(telegram_token)
        print(f"✅ Telegram бот инициализирован")
    else:
        print("⚠️ TELEGRAM_BOT_TOKEN не установлен. Бот отключен.")

@app.get("/")
async def serve_frontend():
    """Перенаправление на главную страницу"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/index.html")

@app.get("/api/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "service": "gorod-kontur-api",
        "version": "2.0.0",
        "features": ["ideas", "analytics", "telegram", "maps"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)