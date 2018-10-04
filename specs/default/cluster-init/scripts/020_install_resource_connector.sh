#!/bin/bash -e

node_template=$(jetpack config cyclecloud.node.template)
if [ "$node_template" != "master" ]; then
	exit 0
fi;

rc_scripts_dir=/usr/share/lsf/10.1/resource_connector/azurecc/scripts

rm -rf $rc_scripts_dir
mkdir -p $rc_scripts_dir
cp -r $CYCLECLOUD_SPEC_PATH/files/host_provider/* $rc_scripts_dir/
chmod +x $rc_scripts_dir/*.sh

yum install -y jre

# TODO RDH make a real init.d script
cat <<EOF > /etc/init.d/mosquitto
#!/bin/bash

(ps aux | grep mosquitto | grep -v grep || /usr/share/lsf/10.1/linux2.6-glibc2.3-x86_64/etc/mosquitto) &
EOF

set +e
adduser mosquitto
set -e

chmod +x /etc/init.d/mosquitto
/etc/init.d/mosquitto

if [ ! -e /usr/share/lsf/resource_connector/ ]; then
	mkdir /usr/share/lsf/resource_connector/
fi

export PYTHONPATH=$rc_scripts_dir/src
python -m add_resource_connector

# enable the demand module
# TODO add this to add_resource_connector
cat /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules | sed -e  s/\#schmod_demand/schmod_demand/ > /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules.tmp
mv /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules.tmp /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules

set +e
source /usr/share/lsf/conf/profile.lsf
set -e


# badmin reconfig -f

set +e
# for jetpack log access
usermod -a -G cyclecloud lsfadmin
set -e


