from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ... import schemas, crud
from ...database import get_db

router = APIRouter()

@router.get("/analytics", response_model=schemas.AnalyticsResponse)
def get_analytics(
    period_days: int = Query(30, le=365),
    db: Session = Depends(get_db)
):
    return crud.get_analytics(db=db, period_days=period_days)