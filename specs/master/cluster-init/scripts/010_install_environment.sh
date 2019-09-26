#!/bin/bash
set +e
$(jetpack config lsf.skip_install | grep -i true) > /dev/null
if [ $? == 0 ]; then
	echo skipping lsf installation
	exit 0
fi;
set -e

lsf_top=$(jetpack config lsf.lsf_top)
set +e
source $lsf_top/conf/profile.lsf
set -e

if [ "$LSF_ENVDIR" == "" ]; then
	echo please define LSF_ENVDIR
	exit 1
fi

if [ "$LSF_SERVERDIR" == "" ]; then
	echo please define LSF_SERVERDIR
	exit 1
fi

yum install -y jre

set +e
adduser mosquitto
set -e
