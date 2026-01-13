from fastapi import APIRouter

router = APIRouter()

@router.get("/telegram/set_webhook")
def set_webhook():
    return {"message": "Use POST /telegram/webhook to set webhook"}