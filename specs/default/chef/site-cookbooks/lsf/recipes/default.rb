#
# Cookbook:: lsf
# Recipe:: default
#
# Copyright:: 2018, The Authors, All Rights Reserved.
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
lsf_top = node['lsf']['lsf_top']

group node['lsf']['admin']['username'] do
  gid '6001'.to_i
end

user node['lsf']['admin']['username'] do
  comment 'lsf Adminstrator'
  uid '6001'.to_i
  gid '6001'.to_i
  home node['lsf']['admin']['home']
  shell '/bin/bash'
end

directory node['lsf']['admin']['home'] do
  user node['lsf']['admin']['username']
  group node['lsf']['admin']['username']
  recursive true
end

execute 'lsfadmin-sshkey' do
  command "ssh-keygen -b 2048 -t rsa -f #{node['lsf']['admin']['home']}/.ssh/id_rsa -q -N \'\' "
  user node['lsf']['admin']['username']
  group node['lsf']['admin']['username']
  creates "#{node['lsf']['admin']['home']}/.ssh/id_rsa"
  not_if { File.exist?("#{node['lsf']['admin']['home']}/.ssh/id_rsa") }
end

execute 'create_auth_keys' do
  command "cp #{node['lsf']['admin']['home']}/.ssh/id_rsa.pub #{node['lsf']['admin']['home']}/.ssh/authorized_keys"
  user node['lsf']['admin']['username']
  group node['lsf']['admin']['username']
  creates "#{node['lsf']['admin']['home']}/.ssh/authorized_keys"
  not_if { File.exist?("#{node['lsf']['admin']['home']}/.ssh/authorized_keys") }
end

file "#{node['lsf']['admin']['home']}/.ssh/config" do
  content <<-EOH
Host *
    StrictHostKeyChecking no
  EOH
  owner node['lsf']['admin']['username']
  group node['lsf']['admin']['username']
  mode '0600'
end

file "/etc/profile.d/lsf.sh" do
  content <<-EOH
source #{node['lsf']['lsf_envdir']}/profile.lsf
  EOH
  mode '644'
end

file '/etc/lsf.sudoers' do
  content "LSF_STARTUP_USERS=\"#{node['lsf']['admin']['username']}\"
LSF_STARTUP_PATH=\"#{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/etc\"
"
  mode '0600'
end
