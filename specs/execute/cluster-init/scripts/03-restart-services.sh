#!/bin/bash -e
lsf_top=$(jetpack config lsf.lsf_top)
set +e
source $lsf_top/conf/profile.lsf
set -e

# point processes to the new lsf.local_etc
export LSF_ENVDIR=$(jetpack config lsf.local_etc /etc/lsf)
lsadmin limstartup -f
lsadmin resstartup -f
badmin hstartup -f

is_submit_only=$(jetpack config lsf.submit_only false)
shopt -s nocasematch
if [ $is_submit_only == "True" ]; then
    badmin close $(hostname)
fi
shopt -u nocasematch

