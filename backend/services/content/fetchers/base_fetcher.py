from typing import List, Dict

def fetch_generic(interest: str) -> List[Dict]:
    """
    Generic fallback fetcher.
    Currently returns a placeholder article.
    """
    return [
        {
            "title": f"Generic article about {interest}",
            "url": "https://example.com",
            "source": "Generic Search"
        }
    ]
