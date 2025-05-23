#!/bin/bash
set -e

node_id=$(python3 ../files/get_node_id.py)

cyclecloud_profile=/tmp/cyclecloud.profile

env_names=$(jetpack config lsf.custom_env_names 0) 2> /dev/null

if [ "$env_names" == "0" ]; then
	echo no custom environment variables defined.
	touch $cyclecloud_profile
else

	for env_name in $env_names; do
		set +e
		value=$(jetpack config lsf.custom_env.$env_name)
		set -e
		if [ $? != 0 ]; then
			echo $env_name is part of lsf.custom_env_names but does not exist under lsf.custom_env
			exit 1
		fi
		
		echo "export $env_name=$value" 1>&2
		echo "export $env_name=$value" >> "$cyclecloud_profile"
	done
fi
echo "export cyclecloud_nodeid=$node_id" >> "$cyclecloud_profile"

chmod +r $cyclecloud_profile
