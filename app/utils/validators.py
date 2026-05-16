import logging
from pydantic import TypeAdapter, AnyHttpUrl, ValidationError

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    #Validates if the provided string is a properly formatted HTTP/HTTPS URL.
    try:
        TypeAdapter(AnyHttpUrl).validate_python(url)
        return True
    except ValidationError as e:
        logger.debug(f"URL validation failed for '{url}': {e.errors()[0]['msg']}")
        return False
