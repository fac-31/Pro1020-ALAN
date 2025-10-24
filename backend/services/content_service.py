import json
from pathlib import Path
from fastapi import HTTPException

SUBSCRIBERS_FILE = Path("subscribers.json")

def load_subscribers():
    if not SUBSCRIBERS_FILE.exists():
        raise HTTPException(status_code=404, detail="subscribers.json not found")
    
    with open(SUBSCRIBERS_FILE, "r") as f:
        return json.load(f)

def generate_content_for_all_interests(subscribers):
    interests = set()
    for subscriber in subscribers:
        for interest in subscriber.get("interests", []):
            interests.add(interest)
    
    generated_content = {interest: f"Generated content for {interest}" for interest in interests}
    return generated_content
