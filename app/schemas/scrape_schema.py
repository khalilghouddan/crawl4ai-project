from typing import List, Optional, Dict, Union, Any
from pydantic import BaseModel, Field

class ScrapeRequest(BaseModel):
    urls: Union[str, List[str]] = Field(..., description="A single URL or a list of URLs to scrape")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom headers for the requests")
    proxy: Optional[str] = Field(None, description="Proxy credentials if any")
    extract_links: bool = Field(False, description="Extract internal links found on the page")
    extract_summary: bool = Field(False, description="Generate an AI-friendly fallback summary")

class ScrapeResultItem(BaseModel):
    url: str
    title: Optional[str] = None
    markdown: Optional[str] = None
    markdown_raw: Optional[str] = None
    summary: Optional[str] = None
    links: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: str
    error: Optional[str] = None

class ScrapeResponse(BaseModel):
    results: List[ScrapeResultItem]
