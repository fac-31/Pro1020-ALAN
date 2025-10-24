# routers/content.py
from fastapi import APIRouter
from services.content_service import load_subscribers, generate_content_for_all_interests

router = APIRouter(
    prefix="/content",
    tags=["content"]
)

@router.get("/")
async def get_content():
    return {"message": "content go here"}

