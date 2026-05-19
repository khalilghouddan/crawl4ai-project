"""HTTP header helpers used by Crawl4AI browser requests."""

import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

def get_random_user_agent() -> str:
    """Return a random desktop browser user-agent string."""
    return random.choice(USER_AGENTS)

def add_referer() -> str:
    """Return the default referer header value."""
    a = "https://www.google.com/"
    return a

def prepare_headers(custom_headers: dict = None) -> dict:
    """Build request headers and merge optional user-provided headers."""
    headers = {} 
    headers["User-Agent"] = get_random_user_agent()
    headers["Referer"] = add_referer()
    
    if custom_headers:
        headers.update(custom_headers)
        
    return headers
