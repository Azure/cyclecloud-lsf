#!/bin/bash
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir/src
args=$@

groups `whoami` | grep cyclecloud > /dev/null
if [ $? = 0 ]; then 
	sg cyclecloud "/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider terminate_machines $args"
	exit $?
else
	/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider terminate_machines $args
	exit $?
fi