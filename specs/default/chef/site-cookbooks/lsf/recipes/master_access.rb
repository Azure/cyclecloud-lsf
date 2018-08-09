
ruby_block "read_pubkey" do
    block do
      node.set['lsf']['admin']['pub_key'] = IO.read('/home/lsfadmin/.ssh/id_rsa.pub').strip
    end
    sensitive true
  end
  
ssh_key_dir = "#{node['lsf']['lsf_top']}/conf/.ssh"
directory ssh_key_dir

file "#{ssh_key_dir}/#{node['hostname']}.pub" do
  content node['lsf']['admin']['pub_key']
  mode '0600'
end

auth_keys = ""
Dir.glob("#{ssh_key_dir}/*.pub") do |pub_key|
  auth_keys << IO.read(pub_key)
  Chef::Log.info("found #{pub_key} with #{auth_keys}")
end

file '/home/lsfadmin/.ssh/authorized_keys' do
  content auth_keys
  owner 'lsfadmin'
  group 'lsfadmin'
  mode '0600'
end

node['lsf']['admin']['access_arrays'].each do |nodearray|
  file "#{node['cyclecloud']['bootstrap']}/#{nodearray}.json" do
    content <<-EOH
    [ { 
        "Configuration" : { "lsf" : { "admin" : 
            { "pub_keys" : 
              { "#{node['cyclecloud']['node']['template']}" : 
                  "#{node['lsf']['admin']['pub_key']}" }
              } 
            } 
          } , "Name" : "#{nodearray}"
          }]
    EOH
  end
  execute "update-pubkey-#{nodearray}" do
    command "jetpack autoscale -f #{node['cyclecloud']['bootstrap']}/#{nodearray}.json"
  end
end