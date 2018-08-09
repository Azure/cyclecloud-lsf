include_recipe "lsf::default"
include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']
master_count = node['lsf']['master']['hostnames'].length

execute "lsf init.d" do
  command "cp #{lsf_top}/10.1/linux2.6-glibc2.3-x86_64/etc/lsf_daemons /etc/init.d/lsf"
  creates "/etc/init.d/lsf"
end

ruby_block 'check_valid_masterlist' do
  block do
    hostname_match = node['lsf']['master']['reverse_hostnames'] == node['lsf']['master']['hostnames']
    raise "Hostname mismatch in master list." if not(hostname_match)
  end
end

template "/usr/share/lsf/conf/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain']
  )
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables(
    :is_slave => false,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
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

