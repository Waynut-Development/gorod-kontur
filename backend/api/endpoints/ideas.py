from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid

from ... import schemas, crud, services
from ...database import get_db

router = APIRouter()

@router.post("/ideas", response_model=schemas.IdeaResponse)
async def create_idea(
    idea: schemas.IdeaCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    db_idea = crud.create_idea(db=db, idea=idea)
    
    # Фоновая задача для анализа идеи
    background_tasks.add_task(
        analyze_idea_task,
        idea_id=str(db_idea.id),
        db=db
    )
    
    return db_idea

@router.get("/ideas", response_model=List[schemas.IdeaResponse])
async def get_ideas(
    category: Optional[str] = Query(None, description="Фильтр по категории"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    priority: Optional[str] = Query(None, description="Фильтр по приоритету"),
    city: Optional[str] = Query("Киселёвск", description="Город"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    ideas = crud.get_ideas(
        db=db,
        category=category,
        status=status,
        skip=skip,
        limit=limit
    )
    return ideas

@router.get("/ideas/prioritized", response_model=schemas.PrioritizedIdeasResponse)
async def get_prioritized_ideas(
    city: str = Query("Киселёвск"),
    limit: int = Query(20, le=50),
    db: Session = Depends(get_db)
):
    all_ideas = crud.get_ideas_by_city(db=db, city=city, limit=100)
    
    prioritizer = services.IdeaPrioritizer()
    city_data = services.DataEnricher.get_city_data(city)
    
    prioritized = []
    for idea in all_ideas:
        context = {
            'similar_ideas': crud.get_similar_ideas(
                db=db, 
                lat=idea.latitude,
                lon=idea.longitude,
                category=idea.category.value
            ),
            'infrastructure_objects': services.DataEnricher.get_infrastructure_objects(
                lat=idea.latitude,
                lon=idea.longitude
            ),
            'city_population': city_data['population']
        }
        
        priority_data = prioritizer.calculate_importance_score(
            idea={
                'latitude': idea.latitude,
                'longitude': idea.longitude,
                'category': idea.category.value,
                'votes_count': idea.votes_count,
                'comments_count': idea.comments_count,
                'created_at': idea.created_at
            },
            context=context
        )
        
        prioritized.append({
            'idea': idea,
            'priority_data': priority_data
        })
    
    prioritized.sort(key=lambda x: x['priority_data']['final_score'], reverse=True)
    
    grouped = {
        'critical': [p for p in prioritized if p['priority_data']['priority'] == 'critical'],
        'high': [p for p in prioritized if p['priority_data']['priority'] == 'high'],
        'medium': [p for p in prioritized if p['priority_data']['priority'] == 'medium'],
        'low': [p for p in prioritized if p['priority_data']['priority'] == 'low']
    }
    
    return {
        'total': len(prioritized),
        'by_priority': grouped,
        'top_critical': [p['idea'] for p in prioritized[:5]],
        'statistics': {
            'critical_count': len(grouped['critical']),
            'high_count': len(grouped['high']),
            'total_score': sum(p['priority_data']['final_score'] for p in prioritized)
        }
    }

@router.get("/ideas/analytics", response_model=schemas.AnalyticsResponse)
async def get_analytics(
    city: str = Query("Киселёвск"),
    period_days: int = Query(30, le=365),
    db: Session = Depends(get_db)
):
    analytics = crud.get_analytics(
        db=db,
        period_days=period_days
    )
    
    # Генерация тепловой карты
    heatmap_data = []
    ideas = crud.get_ideas_by_city(db=db, city=city, limit=1000)
    
    for idea in ideas:
        heatmap_data.append({
            'lat': idea.latitude,
            'lng': idea.longitude,
            'weight': idea.importance_score or 0.5,
            'category': idea.category.value,
            'count': idea.duplicate_count + 1
        })
    
    return {
        'total_ideas': analytics['total_ideas'],
        'active_ideas': analytics['active_ideas'],
        'completed_ideas': analytics['completed_ideas'],
        'total_users': analytics['total_users'],
        'by_category': analytics['by_category'],
        'by_status': analytics['by_status'],
        'by_priority': analytics['by_priority'],
        'heatmap': heatmap_data,
        'trends': analytics['trends']
    }

@router.post("/ideas/{idea_id}/vote")
async def vote_for_idea(
    idea_id: uuid.UUID,
    vote_type: str = Query("up", regex="^(up|down)$"),
    db: Session = Depends(get_db)
):
    user_id = uuid.uuid4()  # Временный ID
    
    vote = crud.create_vote(
        db=db,
        vote=schemas.VoteCreate(idea_id=idea_id, vote_type=vote_type),
        user_id=user_id
    )
    
    return {
        "success": True,
        "message": "Голос учтен",
        "new_votes_count": vote.idea.votes_count
    }

async def analyze_idea_task(idea_id: str, db: Session):
    """Фоновая задача для анализа идеи"""
    from ...ai.categorizer import SimpleAICategorizer
    
    categorizer = SimpleAICategorizer()
    
    # Получаем идею из БД
    idea = crud.get_idea(db, uuid.UUID(idea_id))
    if not idea:
        return
    
    # Анализ категории
    category_result = categorizer.categorize(idea.description, idea.title)
    
    # Обновляем идею
    update_data = {
        'category': category_result['main_category']
    }
    crud.update_idea(db, idea.id, schemas.IdeaUpdate(**update_data))