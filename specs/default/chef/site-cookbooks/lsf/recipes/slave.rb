
include_recipe "lsf::default"
include_recipe "lsf::search_master"

class ::Chef::Resource
  include ::LSF::Helpers
end

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']

execute "lsf init.d" do
  command "cp #{lsf_top}/10.1/linux2.6-glibc2.3-x86_64/etc/lsf_daemons /etc/init.d/lsf"
  creates "/etc/init.d/lsf"
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables(
    :is_slave => true,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
  )
end

template "#{node['lsf']['local_etc']}/lsb.hosts" do
  source 'conf/lsb.hosts.erb'
  variables lazy {{
    :is_master => false
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

defer_block 'defer start of sbatchd to end of run' do
  execute 'badmin hstartup' do 
    command 'source /usr/share/lsf/conf/profile.lsf && badmin hstartup -f'
    not_if 'pidof sbatchd'
    user 'lsfadmin'
    group 'lsfadmin'
  end
end