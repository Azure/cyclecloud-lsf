include_recipe "lsf::default"
include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']

ruby_block 'check_valid_masterlist' do
  block do
    hostname_match = node['lsf']['master']['reverse_hostnames'] == node['lsf']['master']['hostnames']
    Chef::Log.info("Hostname mismatch #{node['lsf']['master']['reverse_hostnames']} != #{node['lsf']['master']['hostnames']}") if not(hostname_match)
    raise "Hostname mismatch in master list." if not(hostname_match)
  end
end

include_recipe "lsf::install"

template "#{node['lsf']['lsf_confdir']}/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain']
  )
end

remote_cluster = node['lsf']['remote_clusters']['default']

template "#{node['lsf']['lsf_confdir']}/lsf.shared" do
  source 'conf/lsf.shared.erb'
  variables(
    :remote_queue => remote_cluster['enabled'],
    :remote_clustername => remote_cluster['clustername'],
    :remote_servers => remote_cluster['servers'].join(" ")
  )
end

cluster_conf_dir = "#{node['lsf']['lsb_confdir']}/#{node['lsf']['clustername']}/configdir"

template "#{cluster_conf_dir}/lsb.queues" do
  source 'conf/lsb.queues.erb'
  variables(
    :remote_queue => remote_cluster['enabled'],
    :queue_name => remote_cluster['queue']['queue_name'],
    :clustername => remote_cluster['clustername']
  )
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables(
    :is_slave => false,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :remote_queue => remote_cluster['enabled'],
    :remote_clustername => remote_cluster['clustername']
  )
end


template "#{node['lsf']['local_etc']}/lsb.hosts" do
  source 'conf/lsb.hosts.erb'
  variables lazy {{
    :is_master => true,
    :master_hostname => node['hostname']
  }}
end

execute 'lsadmin limstartup' do 
  command 'source /usr/share/lsf/conf/profile.lsf && lsadmin limstartup -f'
  not_if 'pidof lim'
  user 'lsfadmin'
  group 'lsfadmin'  
end

execute 'lsadmin resstartup' do 
  command 'source /usr/share/lsf/conf/profile.lsf && lsadmin resstartup -f'
  not_if 'pidof res'
  user 'lsfadmin'
  group 'lsfadmin'
end

execute 'badmin hstartup' do 
  command 'source /usr/share/lsf/conf/profile.lsf && badmin hstartup -f'
  not_if 'pidof sbatchd'
  user 'lsfadmin'
  group 'lsfadmin'
end

execute "lsf init.d" do
  command "cp #{lsf_top}/10.1/linux2.6-glibc2.3-x86_64/etc/lsf_daemons /etc/init.d/lsf"
  creates "/etc/init.d/lsf"
end
