
#python log to track used in big apps 
import logging

def setup_logger(name="scraper_service"):
    #defining the log
    logging.basicConfig(
        level=logging.INFO,
        #format time, level , name , message
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    return logging.getLogger(name)

logger = setup_logger()
