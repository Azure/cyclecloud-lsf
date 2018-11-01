#!/bin/bash
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir/src
args=$@

groups `whoami` | grep cyclecloud > /dev/null
if [ $? = 0 ]; then 
	sg cyclecloud "/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider status $args"
	exit $?s
else
	/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider status $args
	exit $?
fi