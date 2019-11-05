
if node['lsf']['master']['hostnames'].nil?
    cluster_UID = node[:lsf][:master][:clusterUID]
    if cluster_UID.nil?
      cluster_UID = node[:cyclecloud][:cluster][:id]
    end
  
    node_role = node[:lsf][:master][:role]
    if !node_role.nil?
      log "Searching for the LSF master in cluster: #{cluster_UID}, role: #{node_role}" do level :info end
      master_nodes = cluster.search(:clusterUID => cluster_UID, :role => node_role)
    else
      node_recipe = node[:lsf][:master][:recipe]
      if !node_recipe.nil?
        log "Searching for the LSF master in cluster: #{cluster_UID}, recipe: #{node_recipe}" do level :info end
        master_nodes = cluster.search(:clusterUID => cluster_UID, :recipe => node_recipe)
      else
        log "Must specify node[:lsf][:master][:role] or node[:lsf][:master][:recipe] for search." do level :error end
      end
    end

    raise "No master nodes found yet. Retrying on next converge." if master_nodes.length == 0
    # Sort master_nodes by hostname
    #Chef::Log.info("unsorted = #{master_nodes}")
    master_nodes_sorted = master_nodes.sort_by{ |x| x['hostname'] }
    #Chef::Log.info("sorted = #{master_nodes_sorted}")
    Chef::Log.info("Found Master Hostnames = #{ master_nodes_sorted.map{|x| x['hostname']}}")
    node.override['lsf']['master']['hostnames'] = master_nodes_sorted.map{|x| x['hostname']}
    node.override['lsf']['master']['reverse_hostnames'] = master_nodes_sorted.map{|x| get_hostname(x['ipaddress'])}
    Chef::Log.info("Found Master IPs = #{ master_nodes_sorted.map{|x| x['ipaddress']}}")
    node.override['lsf']['master']['ip_addresses'] =  master_nodes_sorted.map{|x| x['ipaddress']}
    node.override['lsf']['master']['fqdns'] =   master_nodes_sorted.map{|x| x['fqdn']}
  
  end