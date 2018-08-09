
default[:lsf][:version] = "10.1"
default['lsf']['clustername'] = "azure"
default['lsf']['tar_dir'] = "/tmp"
default['lsf']['lsf_top'] = "/usr/share/lsf"
default['lsf']['local_etc'] = "/etc/lsf"

default['lsf']['lsb_sharedir'] = "#{node['lsf']['lsf_top']}/work" 
default['lsf']['lsf_confdir'] = "#{node['lsf']['lsf_top']}/conf" 
default['lsf']['lsb_confdir'] = "#{node['lsf']['lsf_top']}/conf/lsbatch" 
default['lsf']['lsf_logdir'] = "#{node['lsf']['lsf_top']}/log" 
default['lsf']['lsf_envdir'] = "#{node['lsf']['lsf_top']}/conf"

default['lsf']['admin']['username'] = 'lsfadmin'
default['lsf']['admin']['home'] = "#{node['lsf']['lsf_top']}/lsfadmin"
default['lsf']['autoscale']['log'] = "/var/log/lsf-autoscale.log"
default['lsf']['execute']['server'] = 1

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
