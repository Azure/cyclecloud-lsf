#!/bin/bash
source /etc/profile.d/lsf.sh
LSF_HOSTNAME=$(hostname | awk '{print tolower($0)}')
if [ -f $LSF_ENVDIR/cyclecloud/remove/$LSF_HOSTNAME ]; then
    mv -f $LSF_ENVDIR/cyclecloud/remove/$LSF_HOSTNAME $LSF_ENVDIR/cyclecloud/is_removed/
    jetpack shutdown --idle
fi