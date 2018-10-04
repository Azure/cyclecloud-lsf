import logging
import os
import sys


def init_logging():
    logpath = os.getenv("CYCLECLOUD_RC_LOGFILE", "/tmp/cyclecloud_rc.log")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    
    logfile_handler = logging.FileHandler(logpath)
    logfile_handler.setLevel(logging.DEBUG)
    logfile_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    logger.addHandler(logfile_handler)
    
    stderr_handler = logging.StreamHandler(stream=sys.stderr)
    stderr_handler.setLevel(logging.DEBUG)
    stderr_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger.addHandler(stderr_handler)
    
    return logger
