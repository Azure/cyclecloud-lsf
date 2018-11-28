#!/bin/bash -e
scriptDir=$(dirname $0)
$scriptDir/./invoke_provider.sh terminate_machines $@
exit $?