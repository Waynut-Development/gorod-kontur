import os
import sys

# Добавляем текущую папку в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn

# Создаем простое приложение
app = FastAPI()

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Простые роуты для проверки
@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/health")
async def health_check():
    return JSONResponse({
        "status": "healthy",
        "service": "gorod-kontur-api",
        "version": "1.0.0"
    })

@app.get("/api/ideas")
async def get_ideas():
    return {
        "ideas": [
            {"id": 1, "title": "Тестовая идея 1", "category": "sport"},
            {"id": 2, "title": "Тестовая идея 2", "category": "ecology"},
        ]
    }

@app.post("/api/ideas")
async def create_idea():
    return {"status": "created", "message": "Идея создана"}

if __name__ == "__main__":
    print("🚀 Запуск упрощенного сервера...")
    print("🌐 Сайт: http://localhost:8000")
    print("🛑 Для остановки нажмите Ctrl+C")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)