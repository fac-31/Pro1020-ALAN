from fastapi import APIRouter, HTTPException
from services.content.content_service import load_subscribers, generate_content_for_all_interests

router = APIRouter(
    prefix="/content",
    tags=["content"]
)

@router.get("/")
async def get_content():
    return {"message": "content go here"}

@router.get("/generate")
async def generate_content():
    """
    Loads subscribers from subscribers.json and generates content for all unique interests.
    """
    try:
        subscribers_data = load_subscribers()
        subscribers = subscribers_data.get("subscribers", [])
        if not subscribers:
            raise HTTPException(status_code=404, detail="No subscribers found in file.")
        
        generated_content = generate_content_for_all_interests(subscribers)
        return {"generated_content": generated_content}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
