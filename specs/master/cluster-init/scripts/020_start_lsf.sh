#!/bin/bash
set -e

lsf_top=$(jetpack config lsf.lsf_top)
set +e
source $lsf_top/conf/profile.lsf
set -e

lsfstartup -f