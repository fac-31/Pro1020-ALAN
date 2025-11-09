from services.content.fetch_page_data import fetch_page_data
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter(prefix="/content", tags=["content"])


class ExtractRequest(BaseModel):
    url: HttpUrl


class ExtractResponse(BaseModel):
    success: bool
    title: str | None = None
    content: str | None = None
    error: str | None = None


@router.post("/extract", response_model=ExtractResponse)
def extract_content(payload: ExtractRequest):
    """
    Extracts the main title and content from the provided URL.

    Example:
    POST /content/extract
    {
        "url": "https://example.com/article"
    }
    """
    result = fetch_page_data(payload.url)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
