#!/bin/bash -e

node_template=$(jetpack config cyclecloud.node.template)
if [ "$node_template" != "master" ]; then
	exit 0
fi;

rm -rf /usr/share/lsf/10.1/resource_connector/azurecc/scripts
mkdir -p /usr/share/lsf/10.1/resource_connector/azurecc/scripts
cp $CYCLECLOUD_SPEC_PATH/files/host_provider/* /usr/share/lsf/10.1/resource_connector/azurecc/scripts/
chmod +x /usr/share/lsf/10.1/resource_connector/azurecc/scripts/*.sh

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

python $CYCLECLOUD_SPEC_PATH/files/python/src/add_resource_connector.py /usr/share/lsf/10.1/resource_connector/hostProviders.json

# enable the demand module
cat /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules | sed -e  s/\#schmod_demand/schmod_demand/ > /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules.tmp
mv /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules.tmp /usr/share/lsf/conf/lsbatch/azure/configdir/lsb.modules

set +e
source /usr/share/lsf/conf/profile.lsf
set -e


# badmin reconfig -f

# chown lsfadmin /opt/cycle/jetpack/logs/jetpack.log
# usermod -a -G cyclecloud lsfadmin ?
set +e
usermod -a -G root lsfadmin
chown -R root: /opt/cycle/jetpack/logs/
set -e


