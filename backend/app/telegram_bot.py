import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
import requests
import uuid
import os

from .database import get_db
from .models import Idea, User
from .schemas import IdeaCreate
from .crud import create_idea
from .services import IdeaPrioritizer

logger = logging.getLogger(__name__)

# Роутер для Telegram
router = APIRouter()

class TelegramBot:
    """Класс для управления Telegram ботом"""
    
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        
    def send_message(self, chat_id: str, text: str, 
                    parse_mode: str = "HTML", 
                    reply_markup: Optional[Dict] = None) -> bool:
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Ошибка отправки в Telegram: {e}")
            return False
    
    def send_idea_notification(self, chat_id: str, idea: Idea) -> bool:
        priority_emojis = {
            "critical": "🔴",
            "high": "🟠", 
            "medium": "🔵",
            "low": "🟢"
        }
        
        category_emojis = {
            "sport": "🏀",
            "art": "🎨",
            "ecology": "🌳",
            "infrastructure": "🛠",
            "education": "📚",
            "culture": "🎭"
        }
        
        emoji = priority_emojis.get(idea.priority or "medium", "⚪")
        cat_emoji = category_emojis.get(idea.category.value, "📌")
        
        message = f"""
{emoji} <b>НОВАЯ ИДЕЯ ОТ ЖИТЕЛЯ</b>

<b>{cat_emoji} Категория:</b> {idea.category.value.upper()}
<b>📌 Заголовок:</b> {idea.title}
<b>📝 Описание:</b> {idea.description[:200]}...

<b>📍 Адрес:</b> {idea.address or 'Не указан'}
<b>🏙 Город:</b> Киселёвск
<b>👤 Автор:</b> Анонимный пользователь

<b>📊 Приоритет:</b> {idea.priority or 'medium'}
<b>⭐ Важность:</b> {idea.importance_score:.2f}/1.0
        """
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "✅ Поддержать", "callback_data": f"vote_up_{idea.id}"},
                {"text": "👎 Против", "callback_data": f"vote_down_{idea.id}"},
                {"text": "🗺 Посмотреть", "url": f"http://localhost:8000/?idea={idea.id}"}
            ]]
        }
        
        return self.send_message(chat_id, message, reply_markup=keyboard)

# Глобальный экземпляр бота
telegram_bot = None

def init_bot(token: str):
    """Инициализация бота при старте приложения"""
    global telegram_bot
    telegram_bot = TelegramBot(token)
    logger.info(f"Telegram бот инициализирован с токеном: {token[:10]}...")

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Вебхук для получения обновлений от Telegram"""
    if not telegram_bot:
        raise HTTPException(status_code=500, detail="Бот не инициализирован")
    
    try:
        data = await request.json()
        logger.debug(f"Получено обновление от Telegram: {data}")
        
        # Обработка callback_query
        if "callback_query" in data:
            callback = data["callback_query"]
            await handle_callback(callback, db)
            
        # Обработка текстовых сообщений
        elif "message" in data and "text" in data["message"]:
            message = data["message"]
            await handle_message(message, db)
            
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Ошибка обработки вебхука: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_callback(callback: Dict, db: Session):
    """Обработка нажатий inline-кнопок"""
    callback_data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]
    
    if callback_data.startswith("vote_up_"):
        idea_id = callback_data.replace("vote_up_", "")
        telegram_bot.send_message(
            chat_id, 
            "✅ Ваш голос учтён! Спасибо за участие.",
            reply_markup={"remove_keyboard": True}
        )
    elif callback_data.startswith("vote_down_"):
        idea_id = callback_data.replace("vote_down_", "")
        telegram_bot.send_message(
            chat_id,
            "👎 Вы проголосовали против этой идеи.",
            reply_markup={"remove_keyboard": True}
        )

async def handle_message(message: Dict, db: Session):
    """Обработка текстовых сообщений"""
    text = message["text"]
    chat_id = message["chat"]["id"]
    
    if text.startswith("/start"):
        welcome_text = """
👋 <b>Добро пожаловать в "Городской Контур"!</b>

Я - бот-помощник платформы для улучшения вашего города.

📌 <b>Доступные команды:</b>
/idea - Предложить новую идею
/list - Посмотреть последние идеи
/stats - Статистика по городу
/help - Помощь по использованию

Просто отправьте мне сообщение с вашей идеей для города!
        """
        telegram_bot.send_message(chat_id, welcome_text)
    
    elif text.startswith("/idea"):
        telegram_bot.send_message(
            chat_id,
            "📝 <b>Предложите идею для города</b>\n\n"
            "Напишите сообщение в формате:\n"
            "<code>Категория: спорт/арт/экология...\n"
            "Заголовок: Ваш заголовок\n"
            "Описание: Подробное описание идеи\n"
            "Адрес: Улица, дом (если известно)</code>\n\n"
            "Или просто опишите вашу идею в одном сообщении."
        )
    
    else:
        await process_idea_from_message(chat_id, text, db)

async def process_idea_from_message(chat_id: str, text: str, db: Session):
    """Создание идеи из сообщения пользователя"""
    try:
        lines = text.split('\n')
        idea_data = {
            "title": "Идея из Telegram",
            "description": text,
            "category": "other",
            "latitude": 54.001,
            "longitude": 37.001,
            "address": "Не указан"
        }
        
        for line in lines:
            if line.lower().startswith("категория:"):
                cat = line.split(":", 1)[1].strip()
                idea_data["category"] = cat
            elif line.lower().startswith("заголовок:"):
                idea_data["title"] = line.split(":", 1)[1].strip()
            elif line.lower().startswith("адрес:"):
                idea_data["address"] = line.split(":", 1)[1].strip()
        
        idea_schema = IdeaCreate(**idea_data)
        idea = create_idea(db=db, idea=idea_schema)
        
        telegram_bot.send_message(
            chat_id,
            f"✅ <b>Идея сохранена!</b>\n\n"
            f"ID: {idea.id}\n"
            f"Статус: Новая\n\n"
            f"Вы можете отслеживать статус идеи на сайте."
        )
        
        # Отправка уведомления в канал
        channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
        if channel_id:
            telegram_bot.send_idea_notification(channel_id, idea)
        
    except Exception as e:
        logger.error(f"Ошибка обработки идеи: {e}")
        telegram_bot.send_message(
            chat_id,
            "❌ <b>Ошибка при сохранении идеи</b>\n\n"
            "Пожалуйста, попробуйте снова или используйте веб-сайт."
        )

@router.post("/notify/{idea_id}")
async def notify_new_idea(idea_id: uuid.UUID, db: Session = Depends(get_db)):
    """Уведомление о новой идеи через Telegram"""
    if not telegram_bot:
        raise HTTPException(status_code=500, detail="Бот не инициализирован")
    
    idea = db.query(Idea).filter(Idea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID", "-1001234567890")
    
    success = telegram_bot.send_idea_notification(channel_id, idea)
    
    if success:
        return {"status": "notification_sent", "channel": channel_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to send notification")