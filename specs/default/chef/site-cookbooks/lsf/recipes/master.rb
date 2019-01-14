include_recipe "lsf::default"
include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
clustername = node['lsf']['clustername']

execute "lsf init.d" do
  command "cp #{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/etc/lsf_daemons /etc/init.d/lsf"
  creates "/etc/init.d/lsf"
end

ruby_block 'check_valid_masterlist' do
  block do
    hostname_match = node['lsf']['master']['reverse_hostnames'] == node['lsf']['master']['hostnames']
    raise "Hostname mismatch in master list." if not(hostname_match)
  end
end

template "#{lsf_top}/conf/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :lsf_top => lsf_top,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain']
  )
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables(
    :is_slave => false,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) }
  )
end

template "#{node['lsf']['local_etc']}/lsb.hosts" do
  source 'conf/lsb.hosts.erb'
  variables lazy {{
    :is_master => true,
    :master_hostname => node['hostname'],
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) }
  }}
end

execute 'lsadmin limstartup' do 
  command "source #{lsf_top}/conf/profile.lsf && lsadmin limstartup -f"
  not_if 'pidof lim'
  user 'lsfadmin'
  group 'lsfadmin'  
end

execute 'lsadmin resstartup' do 
  command "source #{lsf_top}/conf/profile.lsf && lsadmin resstartup -f"
  not_if 'pidof res'
  user 'lsfadmin'
  group 'lsfadmin'
end

execute 'badmin hstartup' do 
  command "source #{lsf_top}/conf/profile.lsf && badmin hstartup -f"
  not_if 'pidof sbatchd'
  user 'lsfadmin'
  group 'lsfadmin'
end

execute "close_master_host" do
  command "source #{lsf_top}/conf/profile.lsf && badmin hclose `hostname` "
  user 'lsfadmin'
  group 'lsfadmin' 
end
