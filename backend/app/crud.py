from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from . import models, schemas

# User CRUD
def get_user(db: Session, user_id: uuid.UUID):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    fake_hashed_password = user.password + "_hashed"  # Заменить на реальное хеширование
    db_user = models.User(
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        hashed_password=fake_hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Idea CRUD
def get_idea(db: Session, idea_id: uuid.UUID):
    return db.query(models.Idea).filter(models.Idea.id == idea_id).first()

def get_ideas(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    query = db.query(models.Idea)
    
    if category:
        query = query.filter(models.Idea.category == category)
    if status:
        query = query.filter(models.Idea.status == status)
    if priority:
        query = query.filter(models.Idea.priority == priority)
    
    return query.order_by(desc(models.Idea.importance_score)).offset(skip).limit(limit).all()

def get_ideas_by_city(db: Session, city: str, limit: int = 100):
    # Простая реализация - в реальности нужна геофильтрация
    return db.query(models.Idea).order_by(desc(models.Idea.created_at)).limit(limit).all()

def create_idea(db: Session, idea: schemas.IdeaCreate, author_id: uuid.UUID = None):
    if author_id is None:
        # Создаём временного пользователя если нет авторизации
        author = get_user_by_email(db, "anonymous@gorod-kontur.ru")
        if not author:
            author = create_user(db, schemas.UserCreate(
                email="anonymous@gorod-kontur.ru",
                full_name="Анонимный пользователь",
                password="anonymous"
            ))
        author_id = author.id
    
    db_idea = models.Idea(
        **idea.dict(),
        author_id=author_id,
        status=models.IdeaStatus.NEW
    )
    db.add(db_idea)
    db.commit()
    db.refresh(db_idea)
    return db_idea

def update_idea(db: Session, idea_id: uuid.UUID, idea_update: schemas.IdeaUpdate):
    db_idea = get_idea(db, idea_id)
    if not db_idea:
        return None
    
    update_data = idea_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_idea, field, value)
    
    db.commit()
    db.refresh(db_idea)
    return db_idea

def get_similar_ideas(db: Session, lat: float, lon: float, category: str, radius: float = 200):
    """Поиск похожих идей в радиусе"""
    # В реальности здесь будет геопоиск по PostGIS
    # Сейчас возвращаем идеи той же категории
    return db.query(models.Idea).filter(
        models.Idea.category == category
    ).limit(10).all()

# Vote CRUD
def create_vote(db: Session, vote: schemas.VoteCreate, user_id: uuid.UUID):
    db_vote = models.Vote(
        idea_id=vote.idea_id,
        user_id=user_id,
        vote_type=vote.vote_type
    )
    
    # Обновляем счётчик голосов в идее
    idea = get_idea(db, vote.idea_id)
    if idea:
        idea.votes_count += 1
    
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)
    return db_vote

# Analytics
def get_analytics(db: Session, period_days: int = 30):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    
    # Базовая статистика
    total_ideas = db.query(func.count(models.Idea.id)).scalar()
    active_ideas = db.query(func.count(models.Idea.id)).filter(
        models.Idea.status.in_([models.IdeaStatus.NEW, models.IdeaStatus.UNDER_REVIEW, models.IdeaStatus.IN_PROGRESS])
    ).scalar()
    completed_ideas = db.query(func.count(models.Idea.id)).filter(
        models.Idea.status == models.IdeaStatus.COMPLETED
    ).scalar()
    total_users = db.query(func.count(models.User.id)).scalar()
    
    # По категориям
    by_category = {}
    for category in models.IdeaCategory:
        count = db.query(func.count(models.Idea.id)).filter(
            models.Idea.category == category,
            models.Idea.created_at >= start_date
        ).scalar()
        by_category[category.value] = count
    
    # По статусам
    by_status = {}
    for status in models.IdeaStatus:
        count = db.query(func.count(models.Idea.id)).filter(
            models.Idea.status == status,
            models.Idea.created_at >= start_date
        ).scalar()
        by_status[status.value] = count
    
    # Топ проблем
    top_problems = db.query(models.Idea).filter(
        models.Idea.importance_score >= 0.7
    ).order_by(desc(models.Idea.importance_score)).limit(5).all()
    
    return {
        "total_ideas": total_ideas or 0,
        "active_ideas": active_ideas or 0,
        "completed_ideas": completed_ideas or 0,
        "total_users": total_users or 0,
        "by_category": by_category,
        "by_status": by_status,
        "by_priority": {"critical": 0, "high": 0, "medium": 0, "low": 0},  # Заглушка
        "top_problems": [{"id": i.id, "title": i.title, "score": i.importance_score} for i in top_problems],
        "trends": {"ideas_per_day": 5, "users_per_day": 2}  # Заглушка
    }