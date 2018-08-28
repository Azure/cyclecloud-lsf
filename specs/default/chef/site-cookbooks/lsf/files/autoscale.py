import subprocess
from subprocess import check_output
import json
import logging
import sys
import time
import os
import pickle
import jetpack.config as jcfg
from pprint import pformat, pprint

def lsf_cmd_call(method_name,call_keys=[],logger=None):
    method_names = ['bjobs', 'bqueues', 'bhosts']
    if method_name not in method_names:
        raise ValueError("method name %s must be one of %s" % (method_name,method_names))
    cmd = [method_name, '-json', '-o'] + [" ".join(call_keys)]
    if method_name == "bjobs":
        cmd += ['-u', 'all']
    logger.debug("cmd = %s" % cmd)

    try:
        stdout = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        logger.error(e.output)
    try:
        _dict = json.loads(stdout)
    except:
        logger.error("invalid json from %s" % cmd)
    if _dict.has_key('RECORDS'):
        return _dict['RECORDS']
    else:
        raise ValueError("Unable to collect RECORDS from %s" % cmd)

def get_jobs_bqueues(queue_name=None,logger=None):
    call_keys = ["QUEUE_NAME","NJOBS"]
    queues = lsf_cmd_call("bqueues", call_keys=call_keys, logger=logger)
    total_jobs = 0
    for queue in queues:
        queue_name = queue['QUEUE_NAME']
        njobs = int(queue['NJOBS'])
        if queue_name:
            if queue_name.lower() != queue_name.lower():
                continue
        total_jobs += njobs
    return total_jobs

def get_jobs_bjobs(logger, queue_name=None):
    call_keys = ["JOBID", "STAT", "QUEUE", "SLOTS"]
    jobs = lsf_cmd_call("bjobs", call_keys=call_keys, logger=logger)
    total_jobs = 0
    for job in jobs:
        job_id = job['JOBID']
        stat = job['STAT']
        queue_name = job['QUEUE']
        slots = int(job['SLOTS'])
        if queue_name:
            if queue_name.lower() != queue_name.lower():
                continue
        total_jobs += slots
    return total_jobs

def get_masters():
    proc1 = subprocess.Popen(['badmin', 'showconf', 'mbd'], stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(['grep', 'LSF_MASTER_LIST' ], stdin=proc1.stdout,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc1.stdout.close()
    out, err = proc2.communicate()
    raw = out.strip().split()
    key_val = 0
    for i,val in enumerate(raw):
        if val == "=":
            key_val = i
    return [x.lower() for x in raw[key_val+1:]]

def get_hosts():
    call_keys = ['HOST_NAME', 'STATUS', 'NJOBS', 'RUN']
    hosts = lsf_cmd_call("bhosts", call_keys=call_keys, logger=logger)
    active_hosts = []
    idle_hosts = []
    for host in hosts:
        hostname = host['HOST_NAME']
        status = host['STATUS']
        njobs = host['NJOBS']
        if status == "closed_Adm" or status == "unavail":
            continue
        if int(njobs) == 0:
            idle_hosts.append(hostname)
        else:
            active_hosts.append(hostname)
    return active_hosts, idle_hosts

def resolve_ip(hostname):
    proc1 = subprocess.Popen(['getent', 'hosts', hostname], stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(['awk', '{print $1}' ], stdin=proc1.stdout,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc1.stdout.close()
    out, err = proc2.communicate()
    return out.strip()


class lsf:

    def __init__(self, logger):
        self.hosts_db_file = '/root/hosts.pkl'
        self.hosts = {}
        self.kill_path = os.path.join(os.environ['LSF_ENVDIR'], "cyclecloud", "remove")
        self.killed_path = os.path.join(os.environ['LSF_ENVDIR'], "cyclecloud", "is_removed")
        self.logger = logger 
        self.masters = get_masters()
        self.njobs = 0
        self.last_seen_max = 90

    def load_hosts(self):
        if os.path.isfile(self.hosts_db_file):
            with open(self.hosts_db_file, 'rb') as f:
                self.hosts = pickle.load(f)
        else:
            self.hosts = {}
    
    def save_hosts(self):
        with open(self.hosts_db_file,'wb') as f:
            pickle.dump(self.hosts, f, protocol=pickle.HIGHEST_PROTOCOL)

    def init_hosts(self, all_hosts):
        ts = time.time()
        for host in all_hosts:
            if self.hosts.has_key(host):
                self.hosts[host]['last_seen'] = ts
            else:
                d = {'first_seen' : ts , 'is_idle' : False, 'last_seen' : ts}
                self.hosts[host] = d

    def update_hosts(self):
        active_hosts, idle_hosts = get_hosts()
        all_hosts = active_hosts + idle_hosts
        self.init_hosts(all_hosts)
        self.update_active_hosts(active_hosts)
        current_hosts = self.hosts.keys()
        orphan_hosts = list(set(current_hosts).difference(set(all_hosts)))
        for orphan_host in orphan_hosts:
            self.hosts.pop(orphan_host)

    def update_active_hosts(self, active_hosts):
        ts = time.time()
        for active_host in active_hosts:
            self.hosts[active_host]['last_active'] = ts

    def check_idle(self):
        ts = time.time()
        killtime_after_jobs = jcfg.get("cyclecloud.cluster.autoscale.idle_time_after_jobs")
        killtime_before_jobs = jcfg.get("cyclecloud.cluster.autoscale.idle_time_before_jobs")
        for hostname, host in self.hosts.iteritems():
            idle = False
            time_since_last_seen = ts - host['last_seen']
            if host.has_key('last_active'):
                time_idle = ts - host['last_active']
                idle = (time_idle > killtime_after_jobs) and (time_since_last_seen < self.last_seen_max)
                time_to_idle_string = "%.1f of %s remaining, last seen %.1f" % (time_idle, killtime_after_jobs, time_since_last_seen)
                if idle:
                    time_to_idle_string += " Host is IDLE - terminating."
            else:
                idle = (ts - host['first_seen'] > killtime_before_jobs) and (time_since_last_seen < self.last_seen_max)
                time_to_idle = ts - host['first_seen']
                time_to_idle_string = "%.1f of %s remaining, last seen %.1f" % (time_to_idle, killtime_before_jobs, time_since_last_seen)
                if idle:
                    time_to_idle_string += " Host is IDLE - terminating."
            host['is_idle'] = idle
            host['time_to_idle'] = time_to_idle_string

    def remove_idle(self):
        for _dir in [self.kill_path, self.killed_path]:
            if not os.path.isdir(_dir):
                os.makedirs(_dir)

        kill_candidates = []
        kill_files = []
        self.logger.debug("check hostnames in master list: %s" % self.masters)
        for hostname, host in self.hosts.iteritems():
            if host['is_idle']:
                if hostname not in self.masters:
                    kill_file = os.path.join(self.kill_path, hostname)
                    if not(os.path.isfile(kill_file)):
                        kill_candidates.append(hostname)
                        kill_files.append(kill_file)
        
        MAX_HCLOSE_LEN = 20
        if kill_candidates.__len__() > MAX_HCLOSE_LEN:
            kill_candidates = kill_candidates[:MAX_HCLOSE_LEN-1]
            kill_files = kill_files[:MAX_HCLOSE_LEN-1]
        
        if not(kill_candidates):
            return

        self.logger.debug("killing %s hosts: %s" % (kill_candidates.__len__(), kill_candidates))
        proc1 = subprocess.Popen(['badmin' , 'hclose'] + kill_candidates)
        out, err = proc1.communicate()
        self.logger.debug("badmin hclose stderr: %s  stdout: %s" % (err, out))
        self.logger.debug("writing killfiles: %s" % kill_files)
        for i,kill_file in enumerate(kill_files):
            self.logger.debug("writing kill file: %s" % kill_file)
            open(kill_file, 'a').close()
            self.hosts.pop(kill_candidates[i])

    def cleanup_markers(self):
        for f in os.listdir(self.killed_path):
            killed_path = os.path.join(self.killed_path,f)
            if os.stat(killed_path).st_mtime < time.time() - 600:
                os.remove(killed_path)

    def get_jobs(self,method):
        if method == "bjobs":
            self.njobs = get_jobs_bjobs(logger=self.logger)
        else:
            self.njobs = get_jobs_bqueues(logger=self.logger)

    def send_autoscale_request(self):
        array = {
            'Name': 'execute',
            'TargetCoreCount': self.njobs
        }
        try:
            logger.debug("autoscale request of %s cores for %s nodearray" % (self.njobs, array['Name']))
            import jetpack.autoscale
            jetpack.autoscale.update([array])
        except Exception as err:
            self.logger.info("jetpack exception: %s" % err)

    def print_hosts(self):
        self.logger.debug(pformat(self.hosts))

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
    h_lsf = lsf(logger)

    if "autostop" in [x.lower() for x in sys.argv]:
        h_lsf.load_hosts()
        h_lsf.update_hosts()
        h_lsf.check_idle()
        h_lsf.remove_idle()
        h_lsf.save_hosts()
        h_lsf.print_hosts()
        h_lsf.cleanup_markers()

    if "autostart" in [x.lower() for x in sys.argv]:
        h_lsf.get_jobs(method="bqueues")
        if "dryrun" in [x.lower() for x in sys.argv]:
            pass
        else:
            h_lsf.send_autoscale_request()
