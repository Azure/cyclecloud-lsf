#!/bin/bash -e
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir/src
args=$@
sg cyclecloud "/opt/cycle/jetpack/system/embedded/bin/python -m cyclecloud_provider templates $args"