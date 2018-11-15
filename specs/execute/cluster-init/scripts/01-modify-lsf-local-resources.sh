#!/bin/bash
set -e

node_template=$(jetpack config cyclecloud.node.template)
if [ "$node_template" == "master" ]; then
	exit 0
fi;

lsf_top=$(jetpack config lsf.lsf_top)
set +e
source $lsf_top/conf/profile.lsf
set -e

if [ "$LSF_ENVDIR" == "" ]; then
	echo please define LSF_ENVDIR
	exit 1
fi

LSF_CONF_FILE=$lsf_top/conf/lsf.conf 


if grep -q LSF_LOCAL_RESOURCES $LSF_CONF_FILE; then
    echo found
else
    echo not found
fi

echo "LSF_LOCAL_RESOURCES=\" [resourcemap ${node_template}*nodearray] [resource azurecchost] \"" >> $LSF_CONF_FILE
