#!/bin/bash
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir/src

embedded_python=/opt/cycle/jetpack/system/embedded/bin/python

if [ -e $embedded_python ]; then
	touch /opt/cycle/jetpack/logs/jetpack.log 1>&2 2> /dev/null
	
	if [ $? == 0 ]; then
		$embedded_python -m cyclecloud_provider $@
		exit $?
	else
		groups $(whoami) | grep -q cyclecloud
		if [ $? != 0 ]; then
			echo $(whoami) must be added to the cyclecloud group.
			exit 1
		else 
			args=$@
			sg cyclecloud "/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider $args"
			exit $?
		fi
	fi
else
	# you'll need requests==2.5.1 installed.
	# > virtualenv ~/.venvs/azurecc
	# > source ~/venvs/azurecc/bin/activate
	# > pip install requests==2.5.1
	python2 -m cyclecloud_provider $@
	exit $?
fi