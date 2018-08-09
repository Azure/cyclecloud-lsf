
include_recipe "lsf::default"
#lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z	lsfsce10.2.0.6-x86_64.tar.gz
#lsf10.1_lsfinstall_linux_x86_64.tar.Z
tar_dir = node['lsf']['tar_dir']
lsf_top = node['lsf']['lsf_top']
clustername = node['lsf']['clustername']

jetpack_download "lsf10.1_lsfinstall_linux_x86_64.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/lsf10.1_lsfinstall_linux_x86_64.tar.Z") }
end

jetpack_download "lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z") }
end

execute "untar_installers" do 
    command "tar -xf lsf10.1_lsfinstall_linux_x86_64.tar.Z"
    cwd tar_dir
    not_if { ::File.exist?("#{tar_dir}/lsf10.1_lsfinstall/lsfinstall") }
end

template "#{tar_dir}/lsf10.1_lsfinstall/lsf.install.config" do
    source 'conf/install.config.erb'
    variables lazy {{
      :master_list => node[:lsf][:master_list].nil? ? node[:hostname] : node[:lsf][:master_list]
    }}
end

execute "run_lsfinstall" do
    command "./lsfinstall -f lsf.install.config"
    cwd "#{tar_dir}/lsf10.1_lsfinstall"
    creates "#{lsf_top}/conf/profile.lsf"
    not_if { ::File.exist?("#{lsf_top}/10.1/linux2.6-glibc2.3-x86_64/lsf_release")}
    not_if { ::Dir.exist?("#{lsf_top}/10.1")}
end

directory node['lsf']['local_etc']

link "#{lsf_top}/conf/lsf.cluster.#{clustername}" do
  to "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}"
end

link "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/lsb.hosts" do
  to "#{node['lsf']['local_etc']}/lsb.hosts"
end