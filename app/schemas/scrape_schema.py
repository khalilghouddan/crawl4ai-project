"""Pydantic request and response schemas for scraping endpoints."""

from typing import List, Optional, Dict, Union, Any, Literal
from pydantic import BaseModel, Field

class ScrapeRequest(BaseModel):
    """Input payload accepted by POST /scrape."""

    urls: Union[str, List[str]] = Field(..., description="A single URL or a list of URLs to scrape")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom headers for the requests")
    proxy: Optional[str] = Field(None, description="Proxy credentials if any")
    extract_links: bool = Field(False, description="Extract internal links found on the page")
    extract_summary: bool = Field(False, description="Generate an AI-friendly fallback summary")

class ScrapeResultItem(BaseModel):
    """One normalized result item returned after a scrape attempt."""

    url: str
    title: Optional[str] = None
    markdown: Optional[str] = None
    markdown_raw: Optional[str] = None
    summary: Optional[str] = None
    links: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Literal["success", "invalid_url", "crawl_error", "empty_content", "timeout", "failed"]
    error: Optional[str] = None
    duration_ms: Optional[int] = None

class ScrapeResponse(BaseModel):
    """Response body containing all scrape results for the request."""

    results: List[ScrapeResultItem]
