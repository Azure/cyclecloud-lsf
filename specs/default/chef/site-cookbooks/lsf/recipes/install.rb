
include_recipe "lsf::default"
#lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z	lsfsce10.2.0.6-x86_64.tar.gz
#lsf10.1_lsfinstall_linux_x86_64.tar.Z
tar_dir = node['lsf']['tar_dir']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
clustername = node['lsf']['clustername']

# lsf10.1_lsfinstall
lsfver = "lsf#{node['lsf']['version']}"

jetpack_download "#{lsfver}_lsfinstall_linux_x86_64.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/#{lsfver}_lsfinstall_linux_x86_64.tar.Z") }
end

jetpack_download "#{lsfver}_linux2.6-glibc2.3-x86_64.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/#{lsfver}_linux2.6-glibc2.3-x86_64.tar.Z") }
end

execute "untar_installers" do 
    command "tar -xf #{lsfver}_lsfinstall_linux_x86_64.tar.Z"
    cwd tar_dir
    not_if { ::File.exist?("#{tar_dir}/#{lsfver}_lsfinstall/lsfinstall") }
end

template "#{tar_dir}/#{lsfver}_lsfinstall/lsf.install.config" do
    source 'conf/install.config.erb'
    variables(
      :master_list => node['lsf']['master']['hostnames'].nil? ? node['hostname'] : node['lsf']['master']['hostnames'].join(" ")
    )
end

# careful that only one of the master nodes does the lsf installation
profile_lsf = "#{lsf_top}/conf/profile.lsf"
execute "run_lsfinstall" do
    command "[[ -f #{profile_lsf} ]] || ./lsfinstall -f lsf.install.config"
    cwd "#{tar_dir}/#{lsfver}_lsfinstall"
    creates profile_lsf
    #not_if { ::File.exist?("#{lsf_top}/#{node['lsf']['version']}/linux2.6-glibc2.3-x86_64/lsf_release")}
    #not_if { ::Dir.exist?("#{lsf_top}/#{node['lsf']['version']}")}
end

directory node['lsf']['local_etc']

link "#{lsf_top}/conf/lsf.cluster.#{clustername}" do
  to "#{node['lsf']['local_etc']}/lsf.cluster.#{clustername}"
end

link "#{lsf_top}/conf/lsbatch/#{clustername}/configdir/lsb.hosts" do
  to "#{node['lsf']['local_etc']}/lsb.hosts"
end