from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from enum import Enum as PyEnum

from .database import Base

class IdeaCategory(str, PyEnum):
    SPORT = "sport"
    ART = "art"
    ECOLOGY = "ecology"
    INFRASTRUCTURE = "infrastructure"
    EDUCATION = "education"
    CULTURE = "culture"
    OTHER = "other"

class IdeaStatus(str, PyEnum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20))
    full_name = Column(String(255))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    points = Column(Integer, default=0)
    telegram_id = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    ideas = relationship("Idea", back_populates="author")
    votes = relationship("Vote", back_populates="user")

class Idea(Base):
    __tablename__ = "ideas"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    category = Column(Enum(IdeaCategory), nullable=False, index=True)
    status = Column(Enum(IdeaStatus), default=IdeaStatus.NEW, index=True)
    
    # Геоданные
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(500))
    
    # Метаданные
    author_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    votes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    duplicate_count = Column(Integer, default=0)
    
    # AI-метрики
    importance_score = Column(Float, default=0.0)
    infrastructure_deficit = Column(Float, default=0.0)
    social_weight = Column(Float, default=0.0)
    
    # Файлы
    photo_urls = Column(JSON, default=list)
    
    # Технические поля
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    author = relationship("User", back_populates="ideas")
    votes = relationship("Vote", back_populates="idea")
    comments = relationship("Comment", back_populates="idea")

class Vote(Base):
    __tablename__ = "votes"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    idea_id = Column(String(36), ForeignKey("ideas.id"), nullable=False)
    vote_type = Column(String(10))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="votes")
    idea = relationship("Idea", back_populates="votes")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    idea_id = Column(String(36), ForeignKey("ideas.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    idea = relationship("Idea", back_populates="comments")

class InfrastructureObject(Base):
    __tablename__ = "infrastructure_objects"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    name = Column(String(255))
    condition = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())