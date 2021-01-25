
include_recipe "lsf::default"
#lsf10.1_linux2.6-glibc2.3-x86_64.tar.Z	lsfsce10.2.0.6-x86_64.tar.gz
#lsf10.1_lsfinstall_linux_x86_64.tar.Z
tar_dir = node['lsf']['tar_dir']
lsf_top = node['lsf']['lsf_top']
lsf_version = node['lsf']['version']
lsf_kernel = node['lsf']['kernel']
lsf_arch = node['lsf']['arch']
lsf_patch = node['lsf']['required_patch_version']
clustername = node['lsf']['clustername']
entitled_install = node['lsf']['entitled_install']

lsf_product = "lsf#{lsf_version}_#{lsf_kernel}-#{lsf_arch}"
lsf_product_fp9 = "lsf#{lsf_version}_#{lsf_kernel}-#{lsf_arch}-#{lsf_patch}"

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

if !lsf_patch.nil?
  jetpack_download "#{lsf_product_fp9}.tar.Z" do
      project "lsf"
      dest tar_dir
      only_if { entitled_install }
      not_if { ::File.exist?("#{tar_dir}/#{lsf_product_fp9}.tar.Z") }
  end
end

#jetpack_download "#{lsf_product_rc_patch}.tar.Z" do
#    project "lsf"
#    dest tar_dir
#    only_if { entitled_install }
#    not_if { ::File.exist?("#{tar_dir}/#{lsf_product_rc_patch}.tar.Z") }
#end

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

execute "anf_fix_lsfprechkfuncs" do
    # update install command to ignore .snapshot dir on ANF
    command "sed -i 's/grep -v lost+found/grep -v lost+found | grep -v .snapshot/g' instlib/lsfprechkfuncs.sh"
    cwd "#{tar_dir}/lsf#{lsf_version}_lsfinstall"
    not_if { ::File.exist?("#{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/lsf_release")}
    not_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
    only_if { ::File.exist?("#{lsf_top}/.snapshot")}
end


yum_package "java-1.8.0-openjdk.x86_64" do
    action "install"
    not_if "yum list installed java-1.8.0-openjdk.x86_64"
  end

# removed pversion dependency
## ./10.1/install/pversions
#IBM Platform LSF 7.0.1 or later not found.

# Also patchinstall is failing
#[Mon Feb 24 21:35:17 UTC 2020:apply_fp_prechk:ERROR_4001]
#    This patch is for LSF 10.1.0 linux3.10-glibc2.17-x86_64. The patch installer cannot find the corresponding LSF base installation. Complete the base installation and make sure the base installation and patch package versions match before applying the patch.

execute "link_package_db" do
    command " ln -s PackageInfo_LSF10.1.0_linux3.10-glibc2.17-x86_64.db Package.db"
    cwd "#{lsf_top}/patch/patchdb/"
    only_if { entitled_install }
    only_if { ::File.exist?("#{lsf_top}/patch/patchdb/PackageInfo_LSF10.1.0_linux3.10-glibc2.17-x86_64.db")}
    only_if { !lsf_patch.nil? }
    creates "#{lsf_top}/patch/patchdb/Package.db"
    action :nothing
end

execute "link_package_db_legacy" do
    command " ln -s PackageInfo_LSF10.1.0_linux2.6-glibc2.3-x86_64.db Package.db"
    cwd "#{lsf_top}/patch/patchdb/"
    only_if { entitled_install }
    only_if { ::File.exist?("#{lsf_top}/patch/patchdb/PackageInfo_LSF10.1.0_linux2.6-glibc2.3-x86_64.db")}
    only_if { !lsf_patch.nil? }
    creates "#{lsf_top}/patch/patchdb/Package.db"
    action :nothing
end

execute "run_lsfinstall_fp9" do
    command " . conf/profile.lsf && ./#{lsf_version}/install/patchinstall --silent #{tar_dir}/#{lsf_product_fp9}.tar.Z"
    cwd "#{lsf_top}"
    only_if { entitled_install }
    only_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
    only_if { ::File.exist?("#{lsf_top}/conf/profile.lsf")}
    only_if { !lsf_patch.nil? }
    not_if  " . conf/profile.lsf && lsid -V | grep #{lsf_patch}", :cwd => "#{lsf_top}"
    action :nothing
end

execute "run_lsfinstall" do
    command "./lsfinstall -f lsf.install.config"
    cwd "#{tar_dir}/lsf#{lsf_version}_lsfinstall"
    creates "#{lsf_top}/conf/profile.lsf"
    not_if { ::File.exist?("#{lsf_top}/#{lsf_version}/#{lsf_kernel}-#{lsf_arch}/lsf_release")}
    not_if { ::Dir.exist?("#{lsf_top}/#{lsf_version}")}
    notifies :run, 'execute[link_package_db]', :immediately
    notifies :run, 'execute[link_package_db_legacy]', :immediately
    notifies :run, 'execute[run_lsfinstall_fp9]', :immediately
end

