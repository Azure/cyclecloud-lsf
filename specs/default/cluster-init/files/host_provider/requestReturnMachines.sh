#!/bin/bash -e
scriptDir=`dirname $0`
export PYTHONPATH=$PYTHONPATH:$scriptDir
/opt/cycle/jetpack/system/embedded/bin/python -m host_provider terminate $@