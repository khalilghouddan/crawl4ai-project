"""Retry policy for transient scraping failures."""

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class ScrapeError(Exception):
    """Raised when a scrape attempt fails in a retryable way."""

    pass

class CrawlError(ScrapeError):
    """Raised when Crawl4AI reports a browser or extraction failure."""

    pass

class EmptyContentError(ScrapeError):
    """Raised when no useful content can be extracted from a page."""

    pass

def get_retry_decorator():
    """Create the Tenacity retry decorator used by scrape operations."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ScrapeError, Exception)),
        reraise=True
    )
