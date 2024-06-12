#!/bin/bash -e

cyclecloud_profile=/tmp/cyclecloud.profile

set +e
source $cyclecloud_profile
set -e

custom_script_uri=$(jetpack config lsf.custom_script_uri 0)

if [ $custom_script_uri == 0 ]; then
	echo lsf.custom_script_uri is not defined, exiting.
	exit
fi

echo running $custom_script_uri...
curl -L $custom_script_uri > /tmp/custom_script_uri_tmp.sh
chmod +x /tmp/custom_script_uri_tmp.sh
/tmp/./custom_script_uri_tmp.sh
rm -f /tmp/custom_script_uri_tmp.sh