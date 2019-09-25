
include_recipe "lsf::default"
#lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z	lsfsce10.2.0.6-x86_64.tar.gz
#lsf10.1_lsfinstall_linux_x86_64.tar.Z
tar_dir = node['lsf']['tar_dir']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
clustername = node['lsf']['clustername']
entitled_install = node['lsf']['entitled_install']

lsf_product = "lsf#{lsf_version}_#{lsf_kernel}-#{lsf_arch}"
lsf_product_sp7 = "lsf#{lsf_version}_#{lsf_kernel}-#{lsf_arch}-509238"
lsf_product_sp8 = "lsf#{lsf_version}_#{lsf_kernel}-#{lsf_arch}-520099"

lsf_install = "lsf#{lsf_version}_lsfinstall_linux_#{lsf_arch}"

jetpack_download "#{lsf_install}.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/#{lsf_install}.tar.Z") }
end

jetpack_download "#{lsf_product}.tar.Z" do
    project "lsf"
    dest tar_dir
    not_if { ::File.exist?("#{tar_dir}/#{lsf_product}.tar.Z") }
end

jetpack_download "#{lsf_product_sp8}.tar.Z" do
    project "lsf"
    dest tar_dir
    only_if { entitled_install }
    not_if { ::File.exist?("#{tar_dir}/#{lsf_product_sp8}.tar.Z") }
end

jetpack_download "lsf_std_entitlement.dat" do
    project "lsf"
    dest tar_dir
    only_if { entitled_install }
    not_if { ::File.exist?("#{tar_dir}/lsf_std_entitlement.dat") }
end

execute "untar_installers" do 
    command "gunzip #{lsf_install}.tar.Z && tar -xf #{lsf_install}.tar"
    cwd tar_dir
    not_if { ::File.exist?("#{tar_dir}/lsf#{lsf_version}_lsfinstall/lsfinstall") }
end

template "#{tar_dir}/lsf#{lsf_version}_lsfinstall/lsf.install.config" do
    source 'conf/install.config.erb'
    variables lazy {{
      :master_list => node[:lsf][:master_list].nil? ? node[:hostname] : node[:lsf][:master_list]
    }}
end

execute "run_lsfinstall" do
    command "./lsfinstall -f lsf.install.config"
    cwd "#{tar_dir}/lsf#{lsf_version}_lsfinstall"
    creates "#{lsf_top}/conf/profile.lsf"
    not_if { ::File.exist?("#{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/lsf_release")}
    not_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
end

execute "run_lsfinstall_sp8" do
    command "tar zxvf #{tar_dir}/#{lsf_product_sp8}.tar.Z"
    cwd "#{lsf_top}/#{lsf_version}"
    only_if { entitled_install }
    not_if  'grep Pack_8 fixlist.txt', :cwd => "#{lsf_top}/#{lsf_version}"
    only_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
end

execute "set_permissions_not_entitled" do
    command "chown -R root:root #{lsf_top} && chmod 4755 #{lsf_top}/10.1/linux*/bin/*admin && touch #{lsf_top}/conf/cyclefixperms"
    not_if { entitled_install }
    only_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
    not_if { ::File.exist?("#{lsf_top}/conf/cyclefixperms")}
end

execute "set_permissions_entitled" do
    command "chown -R root:root #{lsf_top} && chmod 4755 #{lsf_top}/10.1/linux*/bin/*admin && touch #{lsf_top}/conf/cyclefixperms"
    only_if { entitled_install }
    only_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
    only_if  'grep Pack_7 fixlist.txt', :cwd => "#{lsf_top}/#{lsf_version}"
    not_if { ::File.exist?("#{lsf_top}/conf/cyclefixperms")}
end