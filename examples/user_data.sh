#!/bin/bash

LSF_TOP_LOCAL="/grid/lsf"
MASTER_HOSTS_STRING=" ip-0A05000A "

# Default LSF Environment Variables
# rc_account
# template_id 
# providerName (default: cyclecloud)
# clustername cyclecloud

# Custom LSF Environment Variables
# placement_group_id
# nodearray_name

# set LSF_SERVER_HOSTS
sed -i "s/LSF_SERVER_HOSTS=.*/LSF_SERVER_HOSTS=\"${MASTER_HOSTS_STRING}\"/g" ${LSF_TOP_LOCAL}/conf/lsf.conf

# set LSF_LOCAL_RESOURCES
sed -i '/LSF_LOCAL_RESOURCES/d' ${LSF_TOP_LOCAL}/conf/lsf.conf

# assumes templateId == placementGroupName (One template for each placement group)
TEMP_LOCAL_RESOURCES="[resourcemap ${rc_account}*rc_account] [resource cyclecloudhost] [resourcemap ${nodearray_name}*nodearray]"
if [ "$template_id" == "ondemandmpi*" ]; then
    TEMP_LOCAL_RESOURCES="$TEMP_LOCAL_RESOURCES [resource cyclecloudmpi] [resourcemap ${placement_group_id}*placementgroup]"
elif [ "$template_id" == "gpumpi*" ]; then
    TEMP_LOCAL_RESOURCES="$TEMP_LOCAL_RESOURCES [resource cyclecloudmpi] [resourcemap ${placement_group_id}*placementgroup]"
fi

echo "LSF_LOCAL_RESOURCES="\"${TEMP_LOCAL_RESOURCES}\""" >> ${LSF_TOP_LOCAL}/conf/lsf.conf

set +e
source $LSF_TOP_LOCAL/conf/profile.lsf
set -e

# point processes to the new lsf.local_etc
lsadmin limstartup -f
lsadmin resstartup -f
badmin hstartup -f