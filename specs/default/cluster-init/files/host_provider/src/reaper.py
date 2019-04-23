import argparse
import datetime
import json
import logging
import sys

import cluster
import util


util.init_logging(logging.DEBUG, "azurecc_reaper.log", stderr_loglevel=logging.WARN)
provider_config, logger, fine = util.provider_config_from_environment()


def fetch_nodes(clustersapi):
    nodes = clustersapi.get("/cloud/nodes", format="json", cluster=clustersapi.cluster_name)
    response = clustersapi.get("/clusters/%s/status?nodes=true" % clustersapi.cluster_name)
    execute_arrays = {}
    
    node_ids = {}

    for node in response["nodes"]:
        node_ids[node["Name"]] = node["NodeId"]
    
    for nodearray_root in response["nodearrays"]:
        # backward compatability
        nodearray = nodearray_root["nodearray"]
        has_worker_recipe = "recipe[lsf::worker]" in nodearray.get("Configuration", {}).get("run_list", [])
        is_autoscale = nodearray.get("Configuration", {}).get("lsf", {}).get("autoscale", False)
        if has_worker_recipe or is_autoscale:
            execute_arrays[nodearray_root["name"]] = nodearray
    
    ip_to_nodes_ids = {}
    
    for node in nodes:
        node["NodeId"] = node.get("NodeId", node_ids.get(node.get("Name")))
        name = node.get("Name")
        nodearray_name = name.rsplit("-", 1)[0]
        if nodearray_name not in execute_arrays:
            logger.debug("Ignoring node %s because %s is not an execute array (%s)", name, nodearray_name, execute_arrays.keys())
            continue
        node["Configuration"] = execute_arrays[nodearray_name]["Configuration"]
        
        private_ip = node.get("Instance").get("PrivateIp")
        
        if private_ip:
            ip_to_nodes_ids[private_ip] = node
            
    return ip_to_nodes_ids


def fetch_bhosts(subprocess_mod):
    ret = []
    bhosts = subprocess_mod.check_output(["bhosts", "-rconly"]).splitlines(False)
    for line in bhosts:
        line = line.strip()
        toks = line.split()
        if len(toks) == 8 and "PUB_IP_ADDRESS" not in toks:
            private_ip = toks[3]
            
            machine_status = toks[4]
            if machine_status.lower() != "allocated":
                continue
            
            status = toks[5]
            if status != "active":
                continue
            
            ret.append(private_ip)
    return ret


def _sort_by_nodename(a, b):
    # best effort sorting by node name
    try:
        name_a = a.get("Name", "zzzzz-0")
        name_b = b.get("Name", "zzzzz-0")
        
        # somehow the nodename doesn't match our name-index format.
        if "-" not in name_a or "-" not in name_b:
            return name_a.__cmp__(name_b)
        
        template_a = name_a.split("-")[0]
        template_b = name_b.split("-")[0]
        
        if template_a != template_b:
            return template_a.__cmp__(template_b)
        
        node_index_a = name_a.split("-")[-1]
        node_index_b = name_b.split("-")[-1]
        if not node_index_a.isdigit() or not node_index_b.isdigit():
            return 0
        
        if int(node_index_a) < int(node_index_b):
            return -1
        
        return 1
    
    except Exception:
        return 0


def find_timed_out_nodes(nodes, max_boot_time, default_max_failed_time):
    '''
    Finds nodes that have an Instance.StartTime.$date that is older than their respective timeout.
    
    The timeouts are as follows:
        For nodes in the 'Failed' state, the timeout is based on the jetpack.healthcheck.timeout setting on the node, defaulting to 4 hours.
        For nodes in the 'Started' state, the timeout is based on lsf.max_boot_time, defaulting to 75 minutes.
        
        All other nodse are ignored. It is safe to assume that they will eventually reach the Failed state due to a timeout if there is something wrong.
        
    '''
    ret = []
    
    now = datetime.datetime.utcnow()
    for node in nodes:
        status = node["State"]
        if status == "Failed":
            if node.get("InstallJetpack", True):
                timeout = int(node.get("Configuration", {}).get("jetpack", {}).get("healthcheck", {}).get("timeout", 14400))
            else:
                timeout = default_max_failed_time
            reason = "Failed state for longer than %d seconds ago" % timeout
        elif status == "Started":
            timeout = max_boot_time
            reason = "Untracked node that started longer than %ds ago" % timeout
        else:
            logger.debug("Node %s is in state %s, ignoring", node.get("Name"), status)
            continue
        
        start_time_str = node.get("Instance", {}).get("StartTime", {}).get("$date")
        try:
            start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%f+00:00")
        except ValueError:
            try:
                start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S+00:00")
            except ValueError:
                logger.error("Could not parse StartTime for node %s, ignoring - '%s'", node.get("Name"), start_time_str)
                continue
            
        elapsed = (now - start_time).total_seconds()
        if elapsed < 0:
            logging.warn("Elapsed time is negative. CycleCloud and this host do not agree on the date and time.")
            
        ip = node.get("Instance").get("PrivateIp") or "no ip address"
        
        if elapsed > timeout:
            logger.info("Unaccounted for node %s (%s) with status '%s' has timed out (%.0f > %.0f) and will be terminated." % (node.get("Name"), ip, status, elapsed, timeout))
            node["_Reason_"] = reason
            ret.append(node)
        else:
            
            if timeout == 0 or float(elapsed) / timeout > .5: 
                logger.info("Unaccounted for node %s (%s) with status '%s' has not timed out yet (%.0f / %.0f) and will not be terminated." % (node.get("Name"), ip, status, elapsed, timeout))
                
    return ret


def reap(clusterapi, subprocess, hostnamer, writer, write_headers=False, cyclecloud_cli=False, curl=False, max_boot_time=75 * 60, max_failed_time=4 * 3600):
    '''
    Find nodes that exist in CycleCloud but are not being tracked by LSF any longer. Print out useful information that can be used to terminate the machines, optionally
    including cyclecloud cli and autoscale api calls (via curl).
    '''
    try:
        ip_to_nodes_ids = fetch_nodes(clusterapi)
        for ip in fetch_bhosts(subprocess):
            logger.info("Accounted for node with ip %s", ip)
            ip_to_nodes_ids.pop(ip, "")
    except Exception as e:
        if "No nodes were found matching your query" in str(e):
            logger.info("No nodes found. Exiting.")
            return []
        raise
    
    to_shutdown = find_timed_out_nodes(ip_to_nodes_ids.values(), max_boot_time, max_failed_time)
    
    if not to_shutdown:
        return []
    
    machines = []
    
    for node in sorted(to_shutdown, cmp=_sort_by_nodename):
        ip = node.get("Instance", {}).get("PrivateIp")
        hostname = (hostnamer.hostname(ip) if ip else None) or "n/a"
        
        start_time = node.get("Instance", {}).get("StartTime", {}).get("$date") or "n/a"
        
        row = (node["Name"], node["NodeId"], ip, hostname, node["State"], start_time, node["_Reason_"])
       
        if write_headers:
            # construct left-adjusted, minimum size string format expression based on the size of the first row. 
            format_exprs = []
            
            for col in row:
                format_exprs.append("%-" + str(len(col)) + "s")
            complete_format_expr = "\t".join(format_exprs)
            writer.write(complete_format_expr % ("Name", "NodeId", "IP", "Hostname", "State", "StartTime", "Reason"))
            writer.write("\n")
            
            write_headers = False
            
        writer.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(*row))
        machines.append({"machineId": node["NodeId"], "name": hostname, "nodename": node["Name"], "ip": ip, "state": node["State"]})
    
    if (cyclecloud_cli or curl) and machines:
        
        if cyclecloud_cli:
            writer.write("\n")
            
            name_filter = "NodeId in {" + ",".join(['"{}"'.format(x["machineId"]) for x in machines]) + "}"
            writer.write("cyclecloud terminate_nodes {} --filter '{}'\n".format(clusterapi.cluster_name, name_filter))
        
        if curl:
            writer.write("\n")
            
            web_server = clusterapi._get_or_raise("cyclecloud.config.web_server").rstrip("/")
            username = clusterapi._get_or_raise("cyclecloud.config.username")
            url = "{}/clusters/{}/nodes/shutdown".format(web_server, clusterapi.cluster_name)
            post_data = json.dumps({"ids": [x["machineId"] for x in machines]})
            
            writer.write("curl -k -H 'Content-Type: application/json' -u {} '{}' -d '{}' \n".format(username, url, post_data))
            
    logger.info("Found %d machines that can be terminated - %s", len(machines), machines)
    return machines


def main():
    parser = argparse.ArgumentParser()
    
    parser.add_argument("--no-header", default=False, action="store_true", help="Disable printing of the headers.")
    parser.add_argument("--fqdn", default=False, action="store_true", help="Use fully qualified domain name for hostnames.")
    parser.add_argument("--cyclecloud-cli", default=False, action="store_true", help="Print out a cyclecloud cli command to terminate the nodes.")
    parser.add_argument("--curl", default=False, action="store_true", help="Print out curl command to terminate the nodes.")
    parser.add_argument("--max-boot-time", default=4500, type=int, help="Maximum uptime, in seconds, for a fully converged VM to join the cluster " + 
                        "(t=0 being when the VM was started) Default is 75 minutes (4500 seconds)")
    parser.add_argument("--max-failed-time", default=14400, type=int, help="Maximum uptime, in seconds, for a failed node. " + 
                        "(t=0 being when the VM was started). Overridden by cyclecloud.healthcheck.timeout if defined in the nodearray's Configuration section. " +
                        " Default is 4 hours (14400 seconds).")
    parser.add_argument("--output", default="-", help="Output file. Default is stdout")
    
    args = parser.parse_args()
    
    logger.info(" ".join(sys.argv))
    
    hostnamer = util.Hostnamer(args.fqdn)
    cluster_name = provider_config.get("cyclecloud.cluster.name")
    clusterapi = cluster.Cluster(cluster_name, provider_config, logger)
    import subprocess
    
    output = sys.stdout
    close_output = lambda: 0
     
    if args.output != "-":
        output = open(args.output, "w")
        close_output = output.close
    try:
        reap(clusterapi, subprocess, hostnamer, output, not args.no_header, args.cyclecloud_cli, args.curl, args.max_boot_time, args.max_failed_time)
    finally:
        close_output()

    
if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Reaper failed")
        raise
