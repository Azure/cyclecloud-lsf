#!/bin/bash

lsf_top=$(jetpack config lsf.lsf_top .)
lsf_local_etc=$(jetpack config lsf.local_etc /etc/lsf)

mkdir -p $lsf_local_etc

if [ ! -f ${lsf_local_etc}/lsf.conf ]; then
    cp -p ${lsf_top}/conf/lsf.conf ${lsf_local_etc}/
fi
