#!/bin/bash

LSF_TOP_LOCAL="/grid/lsf"
MASTER_HOSTS_STRING=" ip-0A05000A "
printenv > /tmp/user_data.sh.out
# Standard Environment Variables
# rc_account
# providerName (default: cyclecloud)
# clustername cyclecloud
# template_id 

# set local resources
sed -i "s/LSF_SERVER_HOSTS=.*/LSF_SERVER_HOSTS=\"${MASTER_HOSTS_STRING}\"/g" ${LSF_TOP_LOCAL}/conf/lsf.conf

# set lsf server name
sed -i '/LSF_LOCAL_RESOURCES/d' ${LSF_TOP_LOCAL}/conf/lsf.conf

TEMP_LOCAL_RESOURCES="[resourcemap ${rc_account}*rc_account] [resource cyclecloudhost]"
if [ "$template_id" == "ondemandmpipg0" ]; then
    TEMP_LOCAL_RESOURCES="$TEMP_LOCAL_RESOURCES [resource cyclecloudmpi] [resourcemap ${template_id}*placementgroup]"
    TEMP_LOCAL_RESOURCES="$TEMP_LOCAL_RESOURCES [resourcemap ondemandmpi*nodearray]"
fi
echo "LSF_LOCAL_RESOURCES="\"${TEMP_LOCAL_RESOURCES}\""" >> ${LSF_TOP_LOCAL}/conf/lsf.conf

set +e
source $LSF_TOP_LOCAL/conf/profile.lsf
set -e

# point processes to the new lsf.local_etc
lsadmin limstartup -f
lsadmin resstartup -f
badmin hstartup -f