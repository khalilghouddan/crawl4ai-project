



#simple url validation 
def is_valid_url(url: str) -> bool:
    return url.startswith(('http://', 'https://'))
