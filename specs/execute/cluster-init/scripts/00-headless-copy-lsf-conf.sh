#!/bin/bash

IS_HEADLESS=$(jetpack config lsf.headless)
if ! [ "$IS_HEADLESS" == "True" ]; then
  exit 0
fi

LSF_CONF=$(jetpack config lsf.lsf_top .)/conf
LSF_ENVDIR=$(jetpack config lsf.lsf_envdir .)

if [ ! -f $LSF_ENVDIR/lsf.conf ]; then
    if [ -f $LSF_CONF/lsf.conf]; then
      cp -p $LSF_CONF/lsf.conf $LSF_ENVDIR/
    fi
fi
