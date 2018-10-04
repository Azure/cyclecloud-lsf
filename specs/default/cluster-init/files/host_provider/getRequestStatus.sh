#!/bin/bash -e
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir/src
/opt/cycle/jetpack/system/embedded/bin/python -m host_provider status $@