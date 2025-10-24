import json
from pathlib import Path
from fastapi import HTTPException
from services.content.fetchers import tech_fetcher, base_fetcher

SUBSCRIBERS_FILE = Path("subscribers.json")


def load_subscribers():
    if not SUBSCRIBERS_FILE.exists():
        raise HTTPException(status_code=404, detail="subscribers.json not found")
    
    with open(SUBSCRIBERS_FILE, "r") as f:
        return json.load(f)


def fetch_articles_for_interest(interest: str):
    """
    Dispatch interest to the appropriate fetcher:
    - Use tech_fetcher for technology-related topics
    - Fallback to base_fetcher for everything else
    """
    interest_lower = interest.lower()
    
    tech_keywords = ["tech", "technology", "ai", "startups"]
    
    if any(keyword in interest_lower for keyword in tech_keywords):
        return tech_fetcher.fetch_from_hackernews()
    else:
        return base_fetcher.fetch_generic(interest)


def generate_content_for_all_interests(subscribers):
    """
    Generates content for all unique interests across all subscribers
    using the appropriate fetchers.
    """
    interests = set()
    for subscriber in subscribers:
        for interest in subscriber.get("interests", []):
            interests.add(interest)
            print(f'Generating content for {interest}')
    
    generated_content = {}
    for interest in interests:
        articles = fetch_articles_for_interest(interest)
        generated_content[interest] = articles
    
    return generated_content
