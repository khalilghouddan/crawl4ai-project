#just to pik random value 
import random

#the header we change the user agent to avoid being blocked  in the header 
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
]

#function to chose user agent 
def get_random_user_agent() -> str:
    return random.choice(USER_AGENTS)

def add_referer() -> str:
    a = "https://www.google.com/"
    return a

#return th fucking header 
def prepare_headers() -> dict:
    headers = {} 
    headers["User-Agent"] = get_random_user_agent()
    headers["Referer"] = add_referer()
    return headers
