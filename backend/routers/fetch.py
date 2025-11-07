from fastapi import APIRouter
from typing import List, Dict
from services.content.fetch_from_hackernews import fetch_from_hackernews

router = APIRouter(prefix="/fetch", tags=["fetch"])

@router.get("/hackernews", response_model=List[Dict])
def get_hackernews(limit: int = 10):
    """
    Fetch top Hacker News stories.
    """
    stories = fetch_from_hackernews(limit)
    return stories
