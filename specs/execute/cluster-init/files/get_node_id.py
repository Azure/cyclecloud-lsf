import json
import urllib
from subprocess import check_output as check_output_real
import sys

EARLIEST_NODEID_JETPACK_7_VERSION = "7.9.0" 

def check_output(args):
    with open("/dev/null", "w") as stderr:
        return check_output_real(args, stderr=stderr)


def get_node_id_legacy():
    cyclecloud_dict = json.loads(check_output(["jetpack", "config", "cyclecloud", "--json"]))
    cluster_name = cyclecloud_dict["cluster"]["name"].strip()
    username = cyclecloud_dict["config"]["username"].strip()
    password = cyclecloud_dict["config"]["password"].strip()
    web_server = cyclecloud_dict["config"]["web_server"].strip()
    instance_id = cyclecloud_dict["instance"]["id"].strip()
    query_filter = urllib.quote("(ClusterName===\"" + cluster_name + "\"&&InstanceId===\"" + instance_id + "\")")
    nodes_output = check_output(["curl", "-k", "-u", username + ":" + password, web_server + "/db/Cloud.Node?attr=NodeId&f=" + query_filter + "&format=json"])
    nodes = json.loads(nodes_output)
    return nodes[0]["NodeId"]

    #nodes_output = check_output(["curl", "-k", "-u", username + ":" + password, web_server + "/db/Cloud.Node?attr=NodeId&f=(ClusterName===%22" + cluster_name + "%22%26%26InstanceId%3D%3D%22" + instance_id + "%22)&format=json"])
    
def get_node_id():
    jetpack_version = check_output(["jetpack", "-v"]).strip()
    current_version = [int(x.split("-")[0]) for x in jetpack_version.split('.')]
    min_version = [int(x) for x in EARLIEST_NODEID_JETPACK_7_VERSION.split('.')]
    for i in range(min(len(min_version),len(current_version))):
        if current_version[i] < min_version[i]:
            return get_node_id_legacy()
    try:
        return check_output(["jetpack", "config", "cyclecloud.node.id"]).strip()
    except:
        return get_node_id_legacy()

node_id = get_node_id()
if node_id:
    print node_id
else:
    sys.exit(1)