import subprocess
import time

import util


provider_config, logger, fine = util.provider_config_from_environment()


def requeue(job_ids):
    if not job_ids:
        logger.debug("Nothing to requeue")
        return
    
    logger.info("Requeuing %s", ",".join(job_ids))
    
    bkill_cmd = ["bkill", "-r"] + job_ids
    logger.debug("Running command: '%s'", " ".join(bkill_cmd))
    subprocess.check_call(bkill_cmd)
    
    if _can_be_requeued(job_ids):
        brequeue_cmd = ["brequeue", "-e"] + job_ids
        logger.debug("Running command: '%s'", " ".join(brequeue_cmd))
        subprocess.check_call(brequeue_cmd)


def query_jobs():
    '''
    '''
    lines = subprocess.check_output(["bjobs", "-noheader", "-m", "lost_and_found"]).strip().splitlines()
    
    if not lines:
        return []
    
    return [x.split()[0] for x in lines if x.strip()]

    
def _can_be_requeued(job_ids):
    timeout = int(provider_config.get("cyclecloud.lost_and_found.requeue_timeout", 300))
    deadline = timeout + time.time()
    
    while time.time() < deadline:
        hosts = [x.upper() for x in subprocess.check_output(["bjobs", "-noheader", "-o", "STAT"] + job_ids).strip().splitlines()]
        still_lost = len(hosts) - hosts.count("EXIT") 
        
        if still_lost == 0:
            return True
        
        logger.debug("%d still unready to be requeued", still_lost)
        time.sleep(5)
    
    logger.warn("Could not move all jobs out of the lost_and_found host.")
    return False

    
if __name__ == "__main__":
    requeue(query_jobs())
