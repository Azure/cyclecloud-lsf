include_recipe "lsf::default"
include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
clustername = node['lsf']['clustername']
cycle_clustername = node['cyclecloud']['cluster']['name']
username = node['cyclecloud']['config']['username']
web_server = node['cyclecloud']['config']['web_server']

execute "lsf init.d" do
  command "cp #{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/etc/lsf_daemons /etc/init.d/lsf"
  creates "/etc/init.d/lsf"
end

ruby_block 'check_valid_masterlist' do
  block do
    hostname_match = node['lsf']['master']['reverse_hostnames'] == node['lsf']['master']['hostnames']
    raise "Hostname mismatch in master list. #{node[:lsf][:master][:hostnames]} == #{node[:lsf][:master][:reverse_hostnames]}" if not(hostname_match)
  end
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :lsf_top => lsf_top,
    :lsf_clustername => clustername,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain'],
    :master_hostname => node['lsf']['master']['hostnames'][0]
  ) 
end

template "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables(
    :is_slave => false,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
  )
end

template "#{lsf_top}/conf/lsf.shared" do
  source 'conf/lsf.shared.erb'
end

template "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/lsb.queues" do
  source 'conf/lsb.queues.erb'
end

template "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/lsb.modules" do
  source 'conf/lsb.modules.erb'
end

template "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/lsb.params" do
  source 'conf/lsb.params.erb'
end

template "#{lsf_top}/conf/resource_connector/hostProviders.json" do
  source 'conf/hostProviders.json.erb'
end

directory "#{lsf_top}/conf/resource_connector/azurecc/"
template "#{lsf_top}/conf/resource_connector/azurecc/azureccprov_config.json.example" do
  source 'conf/azureccprov_config.json.erb'
  variables(
  	:cycle_clustername => cycle_clustername,
  	:username => username,
  	:web_server => web_server
  )
end

template "#{node['lsf']['local_etc']}/lsb.hosts" do
  source 'conf/lsb.hosts.erb'
  variables lazy {{
    :is_master => true,
    :master_hostname => node['hostname']
  }}
end

defer_block "Defer starting lsf until end of the converge" do
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
end
