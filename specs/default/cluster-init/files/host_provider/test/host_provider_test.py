import unittest
from host_provider import CycleCloudProvider
import json


MACHINE_TYPES = {
    "A4": {"Name": "A4", "CoreCount": 4, "Memory": 1024, "Location": "ukwest"},
    "A8": {"Name": "A8", "CoreCount": 8, "Memory": 2048, "Location": "ukwest"}
    }


class MockCluster:
    def __init__(self, nodearrays):
        self._nodearrays = nodearrays
        # template -> requestI
        self._nodes = {}

    def nodearrays(self):
        return self._nodearrays

    def add_node(self, request):
        '''
                self.cluster.add_node({'Name': nodearray_name,
                                'TargetCount': machine_count,
                                'MachineType': machine_type,
                                "RequestId": request_id,
                                "Configuration": {"lsf": {"user_data": json.dumps(user_data)}}
                                })
        '''
        template = request["Name"]
        target_count = request["TargetCount"]
        machine_type = request["MachineType"]
        configuration = request["Configuration"]
        request_id = request["RequestId"]
        
        if template not in self._nodes:
            self._nodes[template] = []
        node_list = self._nodes[template]

        for i in range(target_count):
            node_index = len(node_list) + i + 1
        
            node_list.append({
                "Name": "%s-%d" % (template, node_index),
                "RequestId": request_id,
                "MachineType": MACHINE_TYPES[machine_type],
                "Configuration": configuration,
                "Status": "Allocating",
                "TargetState": "Ready"
            })
            
    def nodes(self, **attrs):
        '''
        Just yield each node that matches the attrs specified. If the value is a 
        list or set, use 'in' instead of ==
        '''
        def _yield_nodes(**attrs):
            for nodes_for_template in self._nodes.itervalues():
                for node in nodes_for_template:
                    all_match = True
                    for key, value in attrs.iteritems():
                        if isinstance(value, list) or isinstance(value, set):
                            all_match = all_match and node[key] in value
                        else:
                            all_match = all_match and node[key] == value
                    if all_match:
                        yield node
        return list(_yield_nodes(**attrs))
    
    def terminate(self, instance_ids):
        for node in self.nodes():
            if node.get("InstanceId") in instance_ids:
                node["Status"] = "TerminationPreparation"
                node["TargetState"] = "Terminated"
            
            
class Test(unittest.TestCase):

    def test_simple_lifecycle(self):
        cluster = MockCluster([{"Name": "execute", "MachineType": [MACHINE_TYPES["A4"]]}])
        
        def json_writer(data):
            print json.dumps(data, indent=2)
            return data
        
        provider = CycleCloudProvider(cluster, json_writer)
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(1, len(templates))
        self.assertEquals("execute@A4", templates[0]["templateId"])
        self.assertEquals(["Numeric", 4], templates[0]["attributes"]["ncores"])
        self.assertEquals(["Numeric", 2], templates[0]["attributes"]["ncpus"])
        
        cluster._nodearrays.append({"Name": "execute", "MachineType": [MACHINE_TYPES["A8"]]})
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(2, len(templates))
        a4 = [t for t in templates if t["templateId"] == "execute@A4"][0]
        a8 = [t for t in templates if t["templateId"] == "execute@A8"][0]
        
        self.assertEquals(["String", "ukwest"], a4["attributes"]["zone"])
        self.assertEquals(["Numeric", 4], a4["attributes"]["ncores"])
        self.assertEquals(["Numeric", 2], a4["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 1024], a4["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a4["attributes"]["type"])
        
        self.assertEquals(["String", "ukwest"], a8["attributes"]["zone"])
        self.assertEquals(["Numeric", 8], a8["attributes"]["ncores"])
        self.assertEquals(["Numeric", 4], a8["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 2048], a8["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a8["attributes"]["type"])
        
        request = provider.request({"user_data": {},
                                       "rc_account": "default",
                                       "template": {"templateId": "execute@A4",
                                                    "machineCount": 1
                                        }
                                    })
        
        # in Allocation AND we have no instance id == no machine
        statuses = provider.status({
            "requests": [{"requestId": request["requestId"]}]
        })
        
        self.assertEquals("executing", statuses["status"])
        machines = statuses["requests"][0]["machines"]
        self.assertEquals(0, len(machines))

        #        
        # in Allocation AND we have an instance - node should be executing
        mutable_node = cluster.nodes(Name="execute-1")
        mutable_node[0]["InstanceId"] = "i-123"
        mutable_node[0]["Instance"] = {"InstanceId": "i-123", "PrivateIp": "10.0.0.1"}
        mutable_node[0]["LaunchTime"] = 1234567890
        statuses = provider.status({
            "requests": [{"requestId": request["requestId"]}]
        })
        
        self.assertEquals("executing", statuses["status"])
        self.assertEquals(1, len(statuses["requests"]))
        machines = statuses["requests"][0]["machines"]
        self.assertEquals(1, len(machines))
        m = machines[0]
        self.assertEquals("execute-1", m["name"])
        
        #        
        # node is Ready
        mutable_node[0]["Status"] = "Ready"
        statuses = provider.status({
            "requests": [{"requestId": request["requestId"]}]
        })
        self.assertEquals("complete", statuses["status"])
        
        terminate = provider.terminate({
            "machines": [{"machineId": machines[0]["machineId"]}]
        })
        
        self.assertEquals("complete", terminate["status"])


if __name__ == "__main__":
    unittest.main()
