from typing import Dict, Any
import trafilatura
from trafilatura.metadata import extract_metadata
from playwright.sync_api import sync_playwright


def fetch_page_data(url) -> Dict[str, Any]:
    """
    Fetch a webpage and extract its title and main content.

    1. First tries Trafilatura on static HTML.
    2. If extraction fails, falls back to Playwright to render JS content.
    Works with Pydantic HttpUrl or string inputs.
    """
    print(f"[DEBUG] Received URL: {url} (type: {type(url)})")

    if not url:
        return {
            "success": False,
            "title": None,
            "content": None,
            "error": "Invalid URL provided.",
        }

    url_str = str(url)
    print(f"[DEBUG] Using URL string: {url_str}")

    # --- Step 1: Try Trafilatura on static HTML ---
    try:
        downloaded = trafilatura.fetch_url(url_str)
        if downloaded:
            print(f"[DEBUG] Trafilatura fetched HTML length: {len(downloaded)}")
            extracted = trafilatura.extract(
                downloaded, include_comments=False, include_tables=False
            )
            if extracted and len(extracted.strip()) >= 100:
                metadata = extract_metadata(downloaded)
                title = metadata.title if metadata and metadata.title else None
                print(f"[DEBUG] Trafilatura extraction succeeded. Title: {title}")
                return {
                    "success": True,
                    "title": title,
                    "content": extracted.strip(),
                    "error": None,
                }
            else:
                print(
                    "[DEBUG] Trafilatura extraction too short or empty, will try browser fallback."
                )
        else:
            print("[DEBUG] Trafilatura fetch returned None, will try browser fallback.")
    except Exception as e:
        print(f"[DEBUG] Trafilatura error: {e}. Trying browser fallback.")

    # --- Step 2: Fallback to Playwright (headless browser) ---
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            print("[DEBUG] Navigating browser to URL...")
            page.goto(url_str, timeout=20000)
            html = page.content()
            browser.close()

        print(f"[DEBUG] Browser rendered HTML length: {len(html)}")
        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False
        )
        metadata = extract_metadata(html)
        title = metadata.title if metadata and metadata.title else None

        if extracted and len(extracted.strip()) >= 100:
            print(f"[DEBUG] Browser extraction succeeded. Title: {title}")
            return {
                "success": True,
                "title": title,
                "content": extracted.strip(),
                "error": None,
            }
        else:
            print("[DEBUG] Browser extraction too short or empty.")
            return {
                "success": False,
                "title": None,
                "content": None,
                "error": "Could not extract meaningful content even with browser fallback.",
            }

    except Exception as e:
        print(f"[DEBUG] Browser fallback error: {e}")
        return {
            "success": False,
            "title": None,
            "content": None,
            "error": f"Failed to fetch or extract page. {str(e)}",
        }
