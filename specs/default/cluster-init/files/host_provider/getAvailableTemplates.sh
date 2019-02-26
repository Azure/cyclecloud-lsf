#!/bin/bash -e
scriptDir=$(dirname $0)
$scriptDir/./invoke_provider.sh templates $@
exit $?