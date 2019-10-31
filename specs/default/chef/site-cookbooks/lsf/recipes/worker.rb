
include_recipe "lsf::default"
include_recipe "lsf::search_master"

class ::Chef::Resource
  include ::LSF::Helpers
end

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']

# should be done as module in another file
#execute "lsf init.d" do
#  command "cp #{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/etc/lsf_daemons /etc/init.d/lsf"
#  creates "/etc/init.d/lsf"
#end

directory node['lsf']['lsf_logdir'] do
  owner node['lsf']['admin']['username']
  not_if { ::File.directory?(node['lsf']['lsf_logdir']) }
end

directory node['lsf']['local_etc']

template "#{node['lsf']['local_etc']}/lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :lsf_top => lsf_top,
    :master_list => node['lsf']['master']['hostnames'],
    :master_domain => node['domain'],
    :master_hostname => node['lsf']['master']['hostnames'][0]
  )
end

file "/etc/profile.d/set_env_dir.sh" do
  content <<-EOH
export LSF_ENVDIR=#{node['lsf']['local_etc']}
  EOH
  mode '644'
end

#defer_block "Defer starting lsf until end of the converge" do
#  execute 'lsadmin limstartup' do 
#    command "source #{lsf_top}/conf/profile.lsf && LSF_ENVDIR=#{node['lsf']['local_etc']} && lsadmin limstartup -f"
#    not_if 'pidof lim'
#    user 'lsfadmin'
#    group 'lsfadmin'  
#  end
#
#  execute 'lsadmin resstartup' do 
#    command "source #{lsf_top}/conf/profile.lsf && LSF_ENVDIR=#{node['lsf']['local_etc']} && lsadmin resstartup -f"
#    not_if 'pidof res'
#    user 'lsfadmin'
#    group 'lsfadmin'
#  end
#
#  execute 'badmin hstartup' do 
#    command "source #{lsf_top}/conf/profile.lsf && LSF_ENVDIR=#{node['lsf']['local_etc']} && badmin hstartup -f"
#    not_if 'pidof sbatchd'
#    user 'lsfadmin'
#    group 'lsfadmin'
#  end
#
#  execute 'close host' do
#    command "source #{lsf_top}/conf/profile.lsf && badmin hclose #{node['hostname']}"
#    user 'lsfadmin'
#    group 'lsfadmin'
#    only_if { node['lsf']['submit_only'] }
#  end
#end
