import subprocess
from subprocess import check_output
import json
import logging
import sys
import time

class Autoscale():
    def __init__(self, logger):
        self.logger = logger
        self.job_dict = {}

    def get_jobs(self):
        cmd = ['bjobs', '-u', 'all', '-json', '-o', 'jobid stat queue slots']
        self.logger.debug("cmd = %s" % cmd)
        cmd_init = time.time()
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        cmd_elapsed = time.time() - cmd_init
        if cmd_elapsed > 0.05:
            from jetpack import log as jplog
            jplog("bjobs call %.2fs elapsed,stderr = %s" % (cmd_elapsed, stderr), "warn")
            self.logger.warn("bjobs call took longer than 50 ms")
            self.logger.warn("bjobs call %.2fs elapsed,stderr = %s" % (cmd_elapsed, stderr))
        else:
            self.logger.debug("bjobs call %.2fs elapsed,stderr = %s" % (cmd_elapsed, stderr))
        self.job_dict = json.loads(stdout)
        
    def count_jobs(self):
        if self.job_dict.has_key('RECORDS'):
            self.job_count = len(self.job_dict['RECORDS'])
            self.logger.info("%s jobs in queue" % self.job_count)
        else:
            self.logger.info("queue empty")
            self.job_count = 0

    def send_autoscale_request(self):
        array = {
            'Name': 'execute',
            'TargetCoreCount': self.job_count
        }
        try:
            logger.debug("autoscale request of %s cores for %s nodearray" % (self.job_count, "slave"))
            import jetpack.autoscale
            jetpack.autoscale.update([array])
        except Exception as err:
            self.logger.info("jetpack exception: %s" % err)

if __name__ == "__main__":

    if "debug" in [x.lower() for x in sys.argv]:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logger = logging.getLogger('lsf autoscale')
    logger.setLevel(log_level)
    fh = logging.FileHandler("/var/log/lsf-autoscale.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.debug("sys.argv = %s " % sys.argv)

    my_hostname = check_output("hostname").strip().lower()
    master_hostname = check_output("lsid").splitlines()[-1].split()[-1]
    if my_hostname != master_hostname:
        logger.info("This host %s is not the master: %s, Exiting." % (my_hostname, master_hostname))
        sys.exit(0)

    lsfscale = Autoscale(logger)
    lsfscale.get_jobs()
    lsfscale.count_jobs()
    if "dryrun" in [x.lower() for x in sys.argv]:
        pass
    else:
        lsfscale.send_autoscale_request()
