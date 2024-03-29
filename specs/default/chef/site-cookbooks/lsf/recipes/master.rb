include_recipe "lsf::default"


# Store updated host data to ensure searchable list has locally updated hostname
cluster.store_discoverable()
include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
clustername = node['lsf']['clustername']
if node['lsf']['cyclecloud_cluster_name'].nil?
   cycle_clustername = node['cyclecloud']['cluster']['name']
else
  cycle_clustername = node['lsf']['cyclecloud_cluster_name']
end
username = node['cyclecloud']['config']['username']
password = node['cyclecloud']['config']['password']
web_server = node['cyclecloud']['config']['web_server']
region = node['azure']['metadata']['compute']['location']

lsb_conf_dir = "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/"


# Ensure delayed evaluation  of the hostname to catch post-compile-stage changes
lazy_hostname =  lambda {node['hostname']}

ruby_block 'check_valid_masterlist'  do
  block do
    # Check that my own hostname is stable (for runtime hostname changes on first converge)
    # AND that forward and reverse DNS lookups work for all Master nodes in HA configs
    hostname_stable =  node['lsf']['master']['hostnames'].include?(lazy_hostname.call)
    Chef::Log.info "Lazy Hostname = #{lazy_hostname.call} Master List: #{node['lsf']['master']['hostnames']} Stable: #{hostname_stable}"
    hostname_match = node['lsf']['master']['reverse_hostnames'] == node['lsf']['master']['hostnames']
    raise "Hostname mismatch in master list. #{node['lsf']['master']['hostnames']} == #{node['lsf']['master']['reverse_hostnames']}" if not(hostname_match)
    raise "Local hostname changed during converge [ hostname: #{lazy_hostname.call}, master list: #{node['lsf']['master']['hostnames']} ]" if not(hostname_stable)
  end
end

template "#{lsf_top}/conf/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables lazy {{
    :lsf_top => lsf_top,
    :lsf_clustername => clustername,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain'],
    :master_hostname => node['lsf']['master']['hostnames'][0]
  }}
end

template "#{lsf_top}/conf/lsf.cluster.#{clustername}" do
  source 'conf/lsf.cluster.erb'
  variables lazy {{
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) }
  }}
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

template "#{lsf_top}/conf/resource_connector/policy_config.json" do
  source 'conf/policy_config.json.erb'
end

directory "#{lsf_top}/conf/resource_connector/cyclecloud" do
    owner node['lsf']['admin']['username']
end

directory "#{lsf_top}/conf/resource_connector/cyclecloud/conf" do
    owner node['lsf']['admin']['username']
end

template "#{lsf_top}/conf/resource_connector/cyclecloud/conf/cyclecloudprov_config.json" do
  source 'conf/cyclecloudprov_config.json.erb'
  owner 'lsfadmin'
  group 'lsfadmin'
  mode '0600'
  variables(
  	:cycle_clustername => cycle_clustername,
  	:username => username,
  	:password => password,
  	:region => region,
  	:web_server => web_server
  )
end

template "#{lsf_top}/conf/resource_connector/cyclecloud/conf/cyclecloudprov_templates.json" do
  source 'conf/cyclecloudprov_templates.json.erb'
  owner 'lsfadmin'
  group 'lsfadmin'
  mode '0600'
  variables(
    :customscripturi => node['lsf']['custom_script_uri']
  )
end

template "#{lsb_conf_dir}/lsb.hosts" do
  source 'conf/lsb.hosts.erb'
  variables lazy {{
    :master_hostname => node['hostname'],
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) }
    }}
end

directory node['lsf']['lsf_logdir'] do
  owner node['lsf']['admin']['username']
  not_if { ::File.directory?(node['lsf']['lsf_logdir']) }
end

node['lsf']['packages'].each do |p|
  package p do
    action "install"
    not_if "rpm -q #{p}"
  end
end

group "mosquitto" do
  gid '6002'.to_i
end

user "mosquitto" do
  comment 'lsf mosquitto'
  uid '6002'.to_i
  gid '6002'.to_i
end

defer_block "Defer starting lsf until end of the converge" do
  execute 'lsf_deamons start' do 
    command "source #{lsf_top}/conf/profile.lsf && lsf_daemons start"
    not_if 'pidof lim'
    #user 'lsfadmin'
    #group 'lsfadmin'
    #environment(
    #  :PRO_LSF_LOGDIR => node['lsf']['lsf_logdir']
    #)
  end

#  execute 'lsadmin resstartup' do 
#    command "source #{lsf_top}/conf/profile.lsf && lsadmin resstartup -f"
#    not_if 'pidof res'
#    user 'lsfadmin'
#    group 'lsfadmin'
#    environment(
#      :PRO_LSF_LOGDIR => node['lsf']['lsf_logdir']
#    )
#  end
#
#  execute 'badmin hstartup' do 
#    command "source #{lsf_top}/conf/profile.lsf && badmin hstartup -f"
#    not_if 'pidof sbatchd'
#    user 'lsfadmin'
#    group 'lsfadmin'
#    environment(
#      :PRO_LSF_LOGDIR => node['lsf']['lsf_logdir']
#    )
#  end
end
