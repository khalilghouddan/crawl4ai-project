
"""Application logging setup."""

import logging

def setup_logger(name="scraper_service"):
    """Configure and return the named application logger."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    return logging.getLogger(name)

logger = setup_logger()
