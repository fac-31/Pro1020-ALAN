from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/ai", tags=["ai"])


class GenerateTagsRequest(BaseModel):
    text: str


class GenerateTagsResponse(BaseModel):
    tags: List[str]


@router.post("/generate-tags", response_model=GenerateTagsResponse)
def generate_tags_endpoint(payload: GenerateTagsRequest, request: Request):
    """
    Access AIService from app.state and generate tags.
    """
    try:
        ai_service = request.app.state.ai_service
        tags = ai_service.generate_tags(payload.text)
        return GenerateTagsResponse(tags=tags)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to generate tags: {str(e)}"
        )
