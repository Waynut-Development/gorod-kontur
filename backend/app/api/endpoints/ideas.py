from fastapi import APIRouter

router = APIRouter()

@router.get("/ideas")
async def get_ideas():
    return [{"id": 1, "title": "Тестовая идея", "category": "sport"}]

@router.post("/ideas")
async def create_idea():
    return {"status": "created"}