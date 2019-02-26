#!/bin/bash -e
scriptDir=$(dirname $0)
$scriptDir/./invoke_provider.sh create_machines $@
exit $?