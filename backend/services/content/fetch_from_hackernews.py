import requests
from typing import List, Dict

def fetch_from_hackernews(limit: int = 20) -> List[Dict]:
    """
    Fetches top Hacker News stories.
    Returns a list of articles with title, url, and source.
    """
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    try:
        top_ids = requests.get(f"{BASE_URL}/topstories.json", timeout=5).json()[:limit]
        stories = []

        for sid in top_ids:
            story = requests.get(f"{BASE_URL}/item/{sid}.json", timeout=5).json()
            if story.get("type") == "story" and story.get("url"):
                stories.append({
                    "title": story["title"],
                    "url": story["url"],
                    "source": "Hacker News"
                })

        return stories

    except Exception as e:
        print(f"Error fetching from Hacker News: {e}")
        return []