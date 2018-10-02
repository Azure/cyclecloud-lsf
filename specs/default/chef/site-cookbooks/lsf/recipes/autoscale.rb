# install swig 
# clone https://github.com/IBMSpectrumComputing/lsf-python-api.git
# python setup.py build
# yum install gcc
# yum install python-devel

directory node['lsf']['host_tokens_dir'] do
  recursive true
end

file "/etc/logrotate.d/lsf.autoscale.logrotate" do
    content <<-EOH
#{node['lsf']['autoscale']['log']} {
    weekly
    rotate 3
    size 10M
    notifempty
    missingok
}
    EOH
    mode '644'
end

directory '/root/bin'

cookbook_file '/root/bin/autoscale.py' do
  source "autoscale.py"
  mode "0400"
  owner "root"
  group "root"
end

file "/root/bin/autostart.sh" do
  content <<-EOH
source /etc/profile.d/lsf.sh
python /root/bin/autoscale.py -t #{node['lsf']['host_tokens_dir']} debug autostart
  EOH
  mode '500'
end

cron "autostart" do
    command "#{node[:cyclecloud][:bootstrap]}/cron_wrapper.sh /root/bin/autostart.sh"
    only_if { node['cyclecloud']['cluster']['autoscale']['start_enabled'] }
end

file "/root/bin/autostop.sh" do
    content <<-EOH
  source /etc/profile.d/lsf.sh
  python /root/bin/autoscale.py -t #{node['lsf']['host_tokens_dir']} debug autostop
    EOH
    mode '500'
  end
  
  cron "autostop" do
      command "#{node[:cyclecloud][:bootstrap]}/cron_wrapper.sh /root/bin/autostop.sh"
      only_if { node['cyclecloud']['cluster']['autoscale']['stop_enabled'] }
  end