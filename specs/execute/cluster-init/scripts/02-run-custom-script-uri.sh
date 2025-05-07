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
LOCAL_SCRIPT=${CYCLECLOUD_BOOTSTRAP:-/tmp}/custom_script_uri_tmp.sh
curl -L $custom_script_uri > $LOCAL_SCRIPT
chmod +x $LOCAL_SCRIPT
$LOCAL_SCRIPT
rm -f $LOCAL_SCRIPT