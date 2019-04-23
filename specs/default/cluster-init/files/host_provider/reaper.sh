#!/bin/bash -e
scriptDir=$(dirname $0)
export PYTHONPATH=$scriptDir/src

if [ "$PRO_LSF_LOGDIR" == "" ]; then    
    if [ "$LSF_ENVDIR" == "" ]; then
        export PRO_LSF_LOGDIR=/tmp
    else
        export PRO_LSF_LOGDIR=${LSF_ENVDIR}/../log
    fi
fi

if [ ! -e $PRO_LSF_LOGDIR ]; then
    echo $PRO_LSF_LOGDIR does not exist! Setting to cwd. 1>&2
    export PRO_LSF_LOGDIR=$(pwd)
fi

if [ "$PRO_CONF_DIR" == "" ]; then
    if [ "$EGO_TOP" == "" ]; then
        export PRO_CONF_DIR=$(pwd)
    else
        export PRO_CONF_DIR=${LSF_ENVDIR}/resource_connector/azurecc
    fi
fi

echo "Beginning reaper.py at $(date). See $PRO_LSF_LOGDIR/azurecc_reaper.log for more information." 1>&2

embedded_python=/opt/cycle/jetpack/system/embedded/bin/python

if [ -e $embedded_python ]; then
    touch /opt/cycle/jetpack/logs/jetpack.log 1>&2 2> /dev/null

    if [ $? == 0 ]; then
        $embedded_python -m reaper $@
        exit $?
    else
        groups $(whoami) | grep -q cyclecloud
        if [ $? != 0 ]; then
            echo $(whoami) must be added to the cyclecloud group.
            exit 1
        else
            args"=$@"
            sg cyclecloud "/opt/cycle/jetpack/system/embedded/bin/python -m reaper $args"
            exit $?
        fi
    fi
else
    # you'll need requests==2.5.1 installed.
    # > virtualenv ~/.venvs/azurecc
    # > source ~/venvs/azurecc/bin/activate
    # > pip install requests==2.5.1
    python2 -m reaper $@
    exit $?
fi