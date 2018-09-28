#!/bin/bash
set -e

node_template=$(jetpack config cyclecloud.node.template)
if [ "$node_template" != "master" ]; then
	exit 0
fi;

set +e
$(jetpack config lsf.skip_install | grep -i true) > /dev/null
if [ $? == 0 ]; then
	echo skipping lsf installation
	exit 0
fi;
set -e

lsf_top=$(jetpack config lsf.lsf_top)
set +e
source $lsf_top/conf/profile.lsf
set -e

if [ "$LSF_ENVDIR" == "" ]; then
	echo please define LSF_ENVDIR
	exit 1
fi

if [ "$LSF_SERVERDIR" == "" ]; then
	echo please define LSF_SERVERDIR
	exit 1
fi

yum install -y jre

cat <<EOF > /etc/init.d/mosquitto
#!/bin/bash

(ps aux | grep mosquitto | egrep -v 'init.d|grep' || $LSF_SERVERDIR/mosquitto) &
EOF

set +e
adduser mosquitto
set -e

chmod +x /etc/init.d/mosquitto
/etc/init.d/mosquitto
