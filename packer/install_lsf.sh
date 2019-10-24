#!/bin/bash
set -x
cd /tmp
yum install -y ed java-1.8.0-openjdk

groupadd -g 49099 lsfadmin
useradd -d /home/lsfadmin -u 49099 -g 49099 lsfadmin

tar -xf lsf-blobs.tar
tar -xf blobs/lsf10.1_lsfinstall_linux_x86_64.tar.Z

# Requires valid hostnames to install, will update these later.
cp /etc/hosts /etc/hosts.bak
/bin/cat <<EOF >> /etc/hosts
10.5.0.7 ip-0A050007 ip-0A050007
10.5.0.8 ip-0A050008 ip-0A050008
EOF

export LSF_TOP_INSTALL="/grid/lsf"
# LSF_LOCAL_RESOURCES must be valid
FILE="/tmp/install.conf"
/bin/cat <<EOM >$FILE
SILENT_INSTALL="Y"
LSF_TOP="$LSF_TOP_INSTALL"
LSF_ADMINS="lsfadmin"
LSF_TARDIR="/tmp/blobs/"
LSF_ENTITLEMENT_FILE="/tmp/blobs/lsf_std_entitlement.dat"
LSF_SERVER_HOSTS="ip-0A050007 ip-0A050008"
LSF_LOCAL_RESOURCES="[resource cyclecloudhost]"
LSF_LIM_PORT="7869"
ACCEPT_LICENSE="Y"
EOM

pushd lsf10.1_lsfinstall
./lsfinstall -s -f $FILE
cat Install.log
popd

. $LSF_TOP_INSTALL/conf/profile.lsf
$LSF_TOP_INSTALL/10.1/install/patchinstall /tmp/blobs/lsf10.1_lnx310-lib217-x86_64-529611.tar.Z --silent

rm -rf blobs

mv /etc/hosts.bak /etc/hosts