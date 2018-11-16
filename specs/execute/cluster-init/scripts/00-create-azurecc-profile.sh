#!/bin/bash

set -e

lsf_top=$(jetpack config lsf.lsf_top)
azurecc_profile=${lsf_top}/conf/azurecc.profile

env_names=$(jetpack config lsf.custom_env_names 0) 2> /dev/null

if [ "$env_names" == "0" ]; then
	echo no custom environment variables defined.
	touch $azurecc_profile
else

	for env_name in $env_names; do
		set +e
		value=$(jetpack config lsf.custom_env.$env_name)
		set -e
		if [ $? != 0 ]; then
			echo $env_name is part of lsf.custom_env_names but does not exist under lsf.custom_env
			exit 1
		fi
		
		ls $lsf_top/conf 1>&2
		echo "export $env_name=$value" 1>&2
		echo "export $env_name=$value" >> "$azurecc_profile"
	done
fi


chmod +r $azurecc_profile