from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

# Enums
class IdeaCategory(str, Enum):
    SPORT = "sport"
    ART = "art"
    ECOLOGY = "ecology"
    INFRASTRUCTURE = "infrastructure"
    EDUCATION = "education"
    CULTURE = "culture"
    OTHER = "other"

class IdeaStatus(str, Enum):
    NEW = "new"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    points: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Idea schemas
class IdeaBase(BaseModel):
    title: str = Field(..., min_length=5, max_length=500)
    description: str = Field(..., min_length=10)
    category: IdeaCategory
    latitude: float
    longitude: float
    address: Optional[str] = None

class IdeaCreate(IdeaBase):
    pass

class IdeaResponse(IdeaBase):
    id: uuid.UUID
    author_id: uuid.UUID
    status: IdeaStatus
    votes_count: int
    comments_count: int
    duplicate_count: int
    importance_score: float
    infrastructure_deficit: float
    social_weight: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class IdeaUpdate(BaseModel):
    status: Optional[IdeaStatus] = None
    importance_score: Optional[float] = None
    priority: Optional[str] = None

# Vote schemas
class VoteCreate(BaseModel):
    idea_id: uuid.UUID
    vote_type: str = Field(..., regex="^(up|down)$")

class VoteResponse(BaseModel):
    id: uuid.UUID
    idea_id: uuid.UUID
    user_id: uuid.UUID
    vote_type: str
    created_at: datetime

# Analytics schemas
class AnalyticsResponse(BaseModel):
    total_ideas: int
    active_ideas: int
    completed_ideas: int
    total_users: int
    by_category: dict
    by_status: dict
    by_priority: dict
    heatmap: List[dict]
    trends: dict

class PrioritizedIdeasResponse(BaseModel):
    total: int
    by_priority: dict
    top_critical: List[IdeaResponse]
    statistics: dict

# Telegram schemas
class TelegramWebhook(BaseModel):
    update_id: int
    message: Optional[dict] = None
    callback_query: Optional[dict] = None

class TelegramNotification(BaseModel):
    chat_id: str
    text: str
    parse_mode: str = "HTML"
    reply_markup: Optional[dict] = None