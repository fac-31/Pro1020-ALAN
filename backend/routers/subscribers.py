import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict

from services.email_service import EmailService
from email_modules.reply_generator import ReplyGenerator

router = APIRouter()
logger = logging.getLogger(__name__)

SUBSCRIBERS_FILE = 'subscribers.json'

def load_subscribers() -> List[Dict]:
    if not os.path.exists(SUBSCRIBERS_FILE):
        return []
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('subscribers', [])
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading subscribers file: {e}")
        return []

def save_subscribers(subscribers: List[Dict]):
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump({'subscribers': subscribers}, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving subscribers file: {e}")

class SubscribeForm(BaseModel):
    name: str
    email: str
    interests: list[str]

# Dependency: email client
def get_email_client(request: Request) -> EmailService:
    if not hasattr(request.app.state, 'email_client') or not request.app.state.email_client:
        raise HTTPException(status_code=503, detail="Email service is not available.")
    return request.app.state.email_client

# ➕ Dependency: daily digest service
def get_daily_digest_service(request: Request):
    if not hasattr(request.app.state, "digest_service"):
        raise HTTPException(status_code=503, detail="Daily digest service not available")
    return request.app.state.digest_service

# Model for test digest
class DigestTestRequest(BaseModel):
    email: str

@router.post("/subscribe", status_code=201, tags=["Subscribers"])
async def subscribe_user(form: SubscribeForm, email_client: EmailService = Depends(get_email_client)):
    subscribers = load_subscribers()
    if any(s['email'] == form.email for s in subscribers):
        raise HTTPException(status_code=409, detail="Email address is already subscribed.")

    subscribers.append(form.dict())
    save_subscribers(subscribers)

    reply_generator = ReplyGenerator()
    welcome_body = reply_generator.generate_welcome_email(form.name, form.interests)
    
    success = await email_client.send_reply(
        to_email=form.email,
        subject="Welcome to Alan's Newsletter",
        body=welcome_body
    )

    if success:
        return {"status": "subscribed", "email": form.email}
    else:
        logger.error(f"Failed to send welcome email to {form.email}")
        return {"status": "subscribed_email_failed", "email": form.email}

@router.get("/subscribers", tags=["Subscribers"])
def get_subscribers():
    return {"subscribers": load_subscribers()}

@router.delete("/subscribers/{email}", tags=["Subscribers"])
async def unsubscribe_user(email: str):
    subscribers = load_subscribers()
    original_count = len(subscribers)
    
    subscribers = [s for s in subscribers if s['email'] != email]

    if len(subscribers) == original_count:
        raise HTTPException(status_code=404, detail=f"Subscriber with email {email} not found.")

    save_subscribers(subscribers)
    return {"status": "unsubscribed", "email": email}

@router.post("/digest/test", tags=["Digest"])
async def test_daily_digest(
    payload: DigestTestRequest,
    digest_service = Depends(get_daily_digest_service)
):
    """
    Generate a digest immediately for a given email WITHOUT sending an email.
    Useful for debugging the daily digest pipeline.
    """
    subscribers = load_subscribers()
    user = next((s for s in subscribers if s["email"] == payload.email), None)

    if not user:
        raise HTTPException(status_code=404, detail="Subscriber not found")

    interests = user.get("interests", [])
    if not interests:
        raise HTTPException(status_code=400, detail="User has no interests set")

    try:
        digest = await digest_service.generate_daily_digest(
            user_email=payload.email,
            user_interests=interests
        )
        return {
            "email": payload.email,
            "interests": interests,
            "preview": digest
        }
    except Exception as e:
        logger.error(f"Error generating test digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))
