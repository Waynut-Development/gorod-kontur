from fastapi import APIRouter

router = APIRouter()

@router.get("/telegram")
async def get_telegram():
    return {"status": "ok"}