#biblio python to retry a fuction if it faild 
#retry will be decorator
#the otheras parrameters i guess 
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

#i think of error
class ScrapeError(Exception):
    pass

#function that return decorator 
def get_retry_decorator():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((TimeoutError, ScrapeError, Exception)),
        reraise=True
    )
