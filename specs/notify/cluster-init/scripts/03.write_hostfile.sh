#!/usr/bin/env python
import jetpack
import socket
import os
import time
import sys

if __name__ == "__main__":
    instance_id = jetpack.config.get("cyclecloud.instance.id")
    hostname = socket.gethostname().lower()
    host_tokens_dir = jetpack.config.get("lsf.host_tokens_dir")
    hostfile = os.path.join(host_tokens_dir,hostname)
    with open(hostfile, 'a') as f:
        f.write('%s\n%s\n' % (instance_id, time.time()))