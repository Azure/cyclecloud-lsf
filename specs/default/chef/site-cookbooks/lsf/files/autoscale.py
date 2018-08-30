import subprocess
from subprocess import check_output
import json
import logging
import sys
import time
import os
import pickle
import jetpack.config as jcfg
import jetpack.util
from pprint import pformat, pprint
import urllib
import getopt
import socket

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
    closed_hosts = []
    for host in hosts:
        _host = {}
        host['hostname'] = host['HOST_NAME']
        host['status'] = host['STATUS']
        host['njobs'] = int(host['NJOBS'])
    return hosts

def resolve_ip(hostname):
    proc1 = subprocess.Popen(['getent', 'hosts', hostname], stdout=subprocess.PIPE)
    proc2 = subprocess.Popen(['awk', '{print $1}' ], stdin=proc1.stdout,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    proc1.stdout.close()
    out, err = proc2.communicate()
    return out.strip()

def request_shutdown(kill_candidate_ids, kill_candidate_hostfiles, logger, reason=None, config=None):
    """ Requests shutdown from CycleCloud 
    
    Returns True on success (200 OK), False otherwise
    """

    conn, headers = jetpack.util.get_cyclecloud_connection(config)
    configuration = jetpack.util.parse_config(config)

    cluster_name = configuration['identity']['cluster_name']
    instance_id = configuration['identity']['instance_id'] 

    for i, kill_candidate_id in enumerate(kill_candidate_ids):
        url = urllib.quote("/cloud/actions/autoscale/%s/stop" % cluster_name)
        params = {
            "instance": kill_candidate_id
        }
        if reason:
            params['reason'] = reason

        url = url + "?" + urllib.urlencode(params)

        try:
            logger.debug("terminating = kill_candidate_id %s" % kill_candidate_id   )
            conn.request("POST", url, headers=headers)
            r = conn.getresponse()
            if r.status != 200:
                logger.error("kill_candidate_id failed in termination")
        except Exception, e:
            logger.exception("Unable to contact CycleCloud")
        try:
            os.remove(kill_candidate_hostfiles[i])
        except:
            logger.warn("%s already removed." % kill_candidate_hostfiles[i])

class lsf:

    def __init__(self, logger, hostfile_path):
        self.hosts_db_file = '/root/hosts.pkl'
        self.hosts = {}
        self.kill_path = os.path.join(os.environ['LSF_ENVDIR'], "cyclecloud", "remove")
        self.killed_path = os.path.join(os.environ['LSF_ENVDIR'], "cyclecloud", "is_removed")
        self.hostfile_path = hostfile_path
        self.logger = logger 
        self.masters = get_masters() + [socket.gethostname()]
        self.njobs = 0
        self.last_seen_max = 90
        self.tokens_dir = jcfg.get("lsf.host_tokens_dir")


    def load_hosts(self):
        if os.path.isfile(self.hosts_db_file):
            with open(self.hosts_db_file, 'rb') as f:
                self.hosts = pickle.load(f)
        else:
            self.hosts = {}
    
    def save_hosts(self):
        with open(self.hosts_db_file,'wb') as f:
            pickle.dump(self.hosts, f, protocol=pickle.HIGHEST_PROTOCOL)

    def load_hosts_from_tokens(self):
        hostfiles = os.listdir(self.hostfile_path)
        for hostfile in hostfiles:
            fpath = os.path.join(self.hostfile_path, hostfile)
            hostname = hostfile.strip().lower()
            if os.path.isdir(fpath):
                continue
            with open(fpath) as f:
                lines = f.readlines()
                instance_id = lines[0].strip().lower()
                boot_time = float(lines[1].strip())
            if self.hosts.has_key(hostname):
                _host = self.hosts[hostname]
                _host['instance_id'] = instance_id
                _host['boot_time'] = boot_time
            else:
                d = {'boot_time' : boot_time} 
                self.hosts[hostname] = d

    def init_hosts(self, all_hosts):
        ts = time.time()
        for host in all_hosts:
            hostname = host['hostname']
            if self.hosts.has_key(hostname):
                _host = self.hosts[hostname]
                _host['status'] = host['status']
                _host['njobs'] = host['njobs']
                _host['last_seen'] = ts
            else:
                d = {'first_seen' : ts , 
                    'is_idle' : False,
                    'status' : host['status'],
                    'njobs' : host['status'],
                    'last_seen' : ts}
                self.hosts[hostname] = d

    def update_hosts(self):
        all_hosts = get_hosts() 
        available_hosts = [x for x in all_hosts if (x['status'] != "unavail" and x['status'] != "unreach")]
        self.init_hosts(available_hosts)
        active_hosts = [ x for x in available_hosts if x['njobs'] != 0 ]
        ts = time.time()
        for active_host in active_hosts:
            hostname = active_host['hostname']
            self.hosts[hostname]['last_active'] = ts
        current_hosts = self.hosts.keys()
        orphan_hosts = list(set(current_hosts).difference(set([x['hostname'] for x in available_hosts])))
        for orphan_host in orphan_hosts:
            self.hosts.pop(orphan_host)

    def check_idle(self):
        ts = time.time()
        killtime_after_jobs = jcfg.get("cyclecloud.cluster.autoscale.idle_time_after_jobs")
        killtime_before_jobs = jcfg.get("cyclecloud.cluster.autoscale.idle_time_before_jobs")
        for hostname, host in self.hosts.iteritems():
            idle = False
            time_since_last_seen = ts - host['last_seen']
            if time_since_last_seen < self.last_seen_max:
                if host.has_key('last_active'):
                    time_idle = ts - host['last_active']
                    idle = (time_idle > killtime_after_jobs)
                    time_to_idle_string = "%.1f of %s remaining" % (time_idle, killtime_after_jobs)
                    if idle:
                        time_to_idle_string += " Host is IDLE - terminating."
                else:
                    # boot time is weird
                    if host.has_key('boot_time'):
                        t0 = host['boot_time']
                    else:
                        t0 = host['first_seen']
                    idle = (ts - t0 > killtime_before_jobs)
                    time_to_idle = ts - t0
                    time_to_idle_string = "%.1f of %s remaining" % (time_to_idle, killtime_before_jobs)

            host['is_idle'] = idle
            host['time_to_idle'] = time_to_idle_string

    def close_idle(self):
        close_candidates = []
        self.logger.debug("check hostnames in master list: %s" % self.masters)
        for hostname, host in self.hosts.iteritems():
            if host['is_idle'] and host['status'] == "ok" and (hostname not in self.masters):
                close_candidates.append(hostname)
        
        MAX_HCLOSE_LEN = 20
        if close_candidates.__len__() > MAX_HCLOSE_LEN:
            close_candidates = close_candidates[:MAX_HCLOSE_LEN-1]
        
        if not(close_candidates):
            return

        self.logger.debug("closing %s hosts: %s" % (close_candidates.__len__(), close_candidates))
        proc1 = subprocess.Popen(['badmin' , 'hclose'] + close_candidates)
        out, err = proc1.communicate()
        self.logger.debug("badmin hclose stderr: %s  stdout: %s" % (err, out))

    def remove_closed_and_idle(self):
        kill_candidates = []
        kill_candidate_ids = []
        self.logger.debug("check hostnames in master list: %s" % self.masters)
        for hostname, host in self.hosts.iteritems():
            if host['is_idle'] and host['status'] == "closed_Adm" and (hostname not in self.masters):
                kill_candidates.append(hostname)
                kill_candidate_ids.append(host['instance_id'])
        
        if not(kill_candidates):
            return

        self.logger.debug("shutting down hosts: %s, %s" % (kill_candidates, kill_candidate_ids))
        for kill_candidate in kill_candidates:
            hostfile = os.path.join(self.tokens_dir, kill_candidate)
            try:
                os.remove(hostfile)
            except:
                logger.warn("%s already removed." % hostfile)

        kill_candidate_hostfiles = []
        for kill_candidate in kill_candidates:
            hostfile = os.path.join(self.tokens_dir, kill_candidate)
            kill_candidate_hostfiles.append(hostfile)

        request_shutdown(kill_candidate_ids, kill_candidate_hostfiles, self.logger)

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

    myopts, args = getopt.getopt(sys.argv[1:],"t:")
    for opt, arg in myopts:
        if opt == '-t':
            hostfile_path=arg

    logger = logging.getLogger('lsf autoscale')
    logger.setLevel(log_level)
    fh = logging.FileHandler("/var/log/lsf-autoscale.log")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.debug("sys.argv = %s " % sys.argv)
    h_lsf = lsf(logger,hostfile_path)

    if "autostop" in [x.lower() for x in sys.argv]:
        h_lsf.load_hosts()
        h_lsf.load_hosts_from_tokens()
        h_lsf.update_hosts()
        h_lsf.check_idle()
        h_lsf.print_hosts()
        h_lsf.close_idle()
        h_lsf.remove_closed_and_idle()
        h_lsf.save_hosts()

    if "autostart" in [x.lower() for x in sys.argv]:
        h_lsf.get_jobs(method="bqueues")
        if "dryrun" in [x.lower() for x in sys.argv]:
            pass
        else:
            h_lsf.send_autoscale_request()
