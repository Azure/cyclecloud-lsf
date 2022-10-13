
default['lsf']['version'] = "10.1"
default['lsf']['kernel'] = "lnx310-lib217"
default['lsf']['arch'] = "x86_64"
default['lsf']['clustername'] = "cyclecloud"
default['lsf']['tar_dir'] = "/tmp"
default['lsf']['lsf_top'] = "/usr/share/lsf"
default['lsf']['local_etc'] = "/etc/lsf"
default['lsf']['entitled_install'] = true
default['lsf']['accept_license'] = true
default['lsf']['cyclecloud_cluster_name'] = nil
default['lsf']['required_patch_version'] = "532214"

default['lsf']['lsb_sharedir'] = "#{node['lsf']['lsf_top']}/work" 
default['lsf']['lsf_confdir'] = "#{node['lsf']['lsf_top']}/conf" 
default['lsf']['lsb_confdir'] = "#{node['lsf']['lsf_top']}/conf/lsbatch" 
default['lsf']['lsf_logdir'] = "#{node['lsf']['lsf_top']}/log" 
default['lsf']['lsf_envdir'] = "#{node['lsf']['lsf_top']}/conf"

default['lsf']['lsb_rc_query_interval'] = 30
default['lsf']['ebrokerd_host_clean_delay'] = 60
# The LSF default is 60 minutes, which goes against CycleCloud's typical timeout of 5 minutes.
default['lsf']['lsb_rc_external_host_idle_time'] = 5

default['lsf']['admin']['username'] = 'lsfadmin'
default['lsf']['admin']['home'] = "#{node['lsf']['lsf_top']}/lsfadmin"
default['lsf']['autoscale']['log'] = "/var/log/lsf-autoscale.log"

default['lsf']['custom_script_uri'] = "file:///mnt/cluster-init/lsf/execute/files/user_data-full.sh"

case node['platform_family']
when 'suse'
    default['lsf']['packages'] = ["ed"]
end

# Prerequisite packages for LSF to function that need to be installed in the OS
case node['platform']
when 'centos', 'redhat'
    default['lsf']['packages'] = ["java-1.8.0-openjdk.x86_64"]
when 'suse'
    default['lsf']['packages'] += ["java-1_8_0-openjdk"]
when 'sle_hpc', 'sle-hpc'
    default['lsf']['packages'] += ["java-11-openjdk"]
else
    default['lsf']['packages'] = []
end

# for search
default['lsf']['master']['hostnames'] = nil
default['lsf']['master']['ip_addresses'] = nil
default['lsf']['master']['reverse_hostnames'] = nil
default['lsf']['master']['fqdns'] = nil
default['lsf']['master']['cluster'] = nil
default['lsf']['master']['recipe'] = "lsf::master"
default['lsf']['master']['role'] = nil


# Should not need to alter these below:
default[:lsf][:logMask] = "LOG_WARNING"
default[:lsf][:lsfLIMPort]=6322
default[:lsf][:lsfRESPort]=6323
default[:lsf][:lsfMBDPort]=6324
default[:lsf][:lsfSBDPort]=6325
default[:lsf][:lsfAuth]="eauth"
