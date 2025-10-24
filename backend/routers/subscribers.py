import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict

# Add parent directory to path to allow sibling imports
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from email_client import EmailClient

# --- Router Setup ---
router = APIRouter()
logger = logging.getLogger(__name__)

# --- Subscriber Data Management ---
SUBSCRIBERS_FILE = 'subscribers.json'

def load_subscribers() -> List[Dict]:
    """Loads the list of subscribers from subscribers.json."""
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
    """Saves the list of subscribers to subscribers.json."""
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump({'subscribers': subscribers}, f, indent=2)
    except IOError as e:
        logger.error(f"Error saving subscribers file: {e}")

# --- Pydantic Models ---
class SubscribeForm(BaseModel):
    name: str
    email: str
    interests: list[str]

# --- Dependency Injection ---
def get_email_client(request: Request) -> EmailClient:
    """Dependency to get the email client from application state."""
    if not hasattr(request.app.state, 'email_client') or not request.app.state.email_client:
        raise HTTPException(status_code=503, detail="Email service is not available.")
    return request.app.state.email_client

# --- API Endpoints ---
@router.post("/subscribe", status_code=201, tags=["Subscribers"])
async def subscribe_user(form: SubscribeForm, email_client: EmailClient = Depends(get_email_client)):
    """Handle user subscription form submission"""
    subscribers = load_subscribers()
    if any(s['email'] == form.email for s in subscribers):
        raise HTTPException(status_code=409, detail="Email address is already subscribed.")

    subscribers.append(form.dict())
    save_subscribers(subscribers)

    welcome_body = f"Hi {form.name},\n\nThanks for subscribing! Your interests: {', '.join(form.interests)}.\n\nWelcome aboard!\n\nBest,\nAlan"
    
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
    """Return the list of subscribers."""
    return {"subscribers": load_subscribers()}

@router.delete("/subscribers/{email}", tags=["Subscribers"])
async def unsubscribe_user(email: str):
    """Unsubscribe a user by removing them from the subscribers list."""
    subscribers = load_subscribers()
    original_count = len(subscribers)
    
    subscribers = [s for s in subscribers if s['email'] != email]

    if len(subscribers) == original_count:
        raise HTTPException(status_code=404, detail=f"Subscriber with email {email} not found.")

    save_subscribers(subscribers)
    return {"status": "unsubscribed", "email": email}
