include_recipe "lsf::search_master"

clustername = node['lsf']['clustername']
lsf_top = node['lsf']['lsf_top']

directory "C:\\temp" do
  end

jetpack_download "lsf10.1_win-x64.msi" do
    project "lsf"
    dest "C:\\temp"
end

user node['lsf']['admin']['username'] do
    #password "cycl3R0cks!"
end

group "Remote Desktop Users" do
    action :modify
    members [node['lsf']['admin']['username']]
    append true
end

group "Administrators" do
    action :modify
    members [node['lsf']['admin']['username']]
    append true
end

template "C:\\windows\\lsf.conf" do
  source 'conf/lsf.conf.erb'
  variables(
    :lsf_top => lsf_top,
    :lsf_clustername => clustername,
    :master_list => node['lsf']['master']['ip_addresses'].map { |x| get_hostname(x) },
    :master_domain => node['domain'],
    :master_hostname => node['lsf']['master']['hostnames'][0]
  ) 
end

execute "C:\\Windows\\System32\\msiexec /i C:\\temp\\lsf10.1_win-x64.msi SERVERHOSTS=\" #{node['lsf']['master']['hostnames'].join(" ")} \" HOSTTYPE=Server INSTALLDIR=C:\\LSF /quiet" do
    cwd "C:\\temp\\"
   end

# msiexec /i \\hostB\download\lsf10.1_win-x64.msi SERVERHOSTS=hostM HOSTTYPE=Server INSTALLDIR=C:\LSF /quiet
#C:\Windows\System32\msiexec /i C:\Temp\lsf10.1_win-x64.msi SERVERHOSTS="ip-0a05000b ip-0a05000d" HOSTTYPE=Server INSTALLDIR=C:\LSF /quiet

# maybe a win queue?
# set user passwd on windows.
