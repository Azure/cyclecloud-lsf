import argparse
import json
import os
import shutil
import subprocess
import sys
import time

from util import JsonStore


class DryRunHosts:
    '''
    Don't bother actually grabbing the lock, just read the contents
    '''

    def __init__(self, hosts_path):
        self.hosts_path = hosts_path

    def __enter__(self):
        return json.load(open(self.hosts_path))

    def __exit__(self, *args):
        pass


def fix_blackholes(dry_run):
    env_dir = os.getenv("LSF_ENVDIR")
    if not env_dir:
        print >> sys.stderr, "Please source profile.lsf before running this"
        sys.exit(1)

    work_dir = os.path.join(env_dir, "../work/azurecc/resource_connector")
    hosts_json = JsonStore("hosts.json", work_dir, formatted=True)
    hosts_path = os.path.join(work_dir, "hosts.json")
    if dry_run:
        hosts_json = DryRunHosts()
    else:
        backup_path = "%s.%s" % (hosts_path, time.time())
        print "Making a backup to", backup_path
        shutil.copyfile(hosts_path, backup_path)

    for line in subprocess.check_output(["ps", "aux"]).splitlines():
        if "ebrokerd" in line:
            toks = line.split()
            pid = toks[1]
            print "> kill -9", pid
            if not dry_run:
                subprocess.check_call(["kill", "-9", pid])

    at_least_one = False
    with hosts_json as hosts:
        for host in hosts["hosts"]:
            if host["state"] == "Deallocated_Sent" and host["machineState"] == "active":
                at_least_one = True
                print ">>>", host["name"], "state=Deallocated_Sent -> Done"
                print ">>>", host["name"], "machineState=active -> deleted"
                if not dry_run:
                    host["state"] = "Done"
                    host["machineState"] = "deleted"
                    
    if not at_least_one:
        print "No hosts found in Deallocated_Sent / active state."
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", default=False, action="store_true")
    args = parser.parse_args()
    fix_blackholes(args.dry_run)
