#!/bin/bash -e

lsf_top=$(jetpack config lsf.lsf_top)
cyclecloud_profile=$(jetpack config lsf.local_etc /etc/lsf)/cyclecloud.profile

set +e
source $cyclecloud_profile
set -e

custom_script_uri=$(jetpack config lsf.custom_script_uri 0)

if [ $custom_script_uri == 0 ]; then
	echo lsf.custom_script_uri is not defined, exiting.
	exit
fi

echo running $custom_script_uri...
curl $custom_script_uri > custom_script_uri_tmp.sh
chmod +x custom_script_uri_tmp.sh
./custom_script_uri_tmp.sh