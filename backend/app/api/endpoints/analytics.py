from fastapi import APIRouter

router = APIRouter()

@router.get("/analytics")
async def get_analytics():
    return {"total": 0}