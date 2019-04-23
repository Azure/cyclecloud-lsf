import unittest
import datetime
import reaper
import uuid
from util import ProviderConfig
import cStringIO


class MockCluster:
    
    def __init__(self, nodes):
        self._nodes = nodes
        self.cluster_name = "mock"
        self._nodes.append({"Name": "master-1", "NodeId": "00000"})
        self.provider_config = ProviderConfig({})
    
    def get(self, url, **ignore):
        if url.startswith("/cloud/nodes"):
            return self._nodes
        elif url.startswith("/clusters"):
            nodes = []
            for node in self._nodes:
                nodes.append({"Name": node.get("Name"), "NodeId": str(uuid.uuid4()),})
            return {"nodearrays": [{"name": "execute", "nodearray": {"Configuration": {"lsf": {"autoscale": True}}}},
                                   {"name": "master", "nodearray": {}}],
                    "nodes": nodes}
    

class MockSubprocess:
    
    def __init__(self, hosts):
        self._output = ""
        for ip, machine_state, state in hosts:
            self._output += "\n- - - %s %s %s - -" % (ip, machine_state, state)
        
    def check_output(self, args):
        return self._output
    

class MockHostnamer:
    
    def hostname(self, ip):
        return "ip-%s" % ip.replace(".", "-")
    
    def private_ip_address(self, hostname):
        return hostname.replace("ip-", "").replace("-", ".")


class ReaperTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.nodeindex = 1

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        
    def _node(self, state, since_started, private_ip=None):
        name = "execute-%d" % self.nodeindex
        self.nodeindex += 1
        timestampformat = "%Y-%m-%dT%H:%M:%S.%f+00:00"
        now = datetime.datetime.utcnow()
        start_time = datetime.datetime.strftime(now - datetime.timedelta(0, since_started), timestampformat)
        
        return {"Name": name, "Status": state, "State": state, 
                "Instance": {"StartTime": {"$date": start_time},
                             "PrivateIp": private_ip}}

    def test_reap_zombie_started_node(self):
        subprocess = MockSubprocess([("10.0.0.1", "Done", "deleted"),
                                     ("10.0.0.2", "Done", "deleted"),
                                     ("10.0.0.3", "Allocated", "active"),
                                     ("10.0.0.5", "Dellocated_Sent", "active")])
        hostnamer = MockHostnamer()
        
        #
        # zombie active node that hasn't quite hit our timeout
        clusterapi = MockCluster([self._node("Started", 75 * 60 - 10, "10.0.0.2"),
                                  self._node("Started", 75 * 60 - 10, "10.0.0.5"),
                                  self._node("Started", 10, "10.0.0.3")])
        writer = cStringIO.StringIO()
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(0, len(machines))
        
        #
        # zombie active node that has hit our timeout
        clusterapi = MockCluster([self._node("Started", 75 * 60 + 10, "10.0.0.2"),
                                  self._node("Started", 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 1)
        self.assertEquals(machines.pop(0)["ip"], "10.0.0.2")
        
        # repeat with 10.0.0.5, which is in active state but Deallocated_Sent
        clusterapi = MockCluster([self._node("Started", 75 * 60 + 10, "10.0.0.5"),
                                  self._node("Started", 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 1)
        self.assertEquals(machines.pop(0)["ip"], "10.0.0.5")
        
        #
        # a node stuck in allocation for a long time - should be ignored
        # will eventually get picked up by health check
        clusterapi = MockCluster([self._node("Allocation", 75 * 60 + 10, "10.0.0.2"),
                                  self._node("Allocation", 75 * 60 + 10, "10.0.0.5"),
                                  self._node("Started", 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 0)
        
        #
        # a failed node before health check
        clusterapi = MockCluster([self._node("Failed", 4 * 3600 - 10, "10.0.0.2"),
                                  self._node("Failed", 4 * 3600 - 10, "10.0.0.5"),
                                  self._node("Started", 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 0)
        
        #
        # a failed node after health check
        clusterapi = MockCluster([self._node("Failed", 4 * 3600 + 10, "10.0.0.2"),
                                  self._node("Started", 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 1)
        self.assertEquals(machines.pop(0)["ip"], "10.0.0.2")

        #
        # an accounted for node - doesn't matter how long it is started, it is active according to bhosts        
        clusterapi = MockCluster([self._node("Started", 75 * 60 + 10, "10.0.0.3")])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 0)
        
        #
        # bhosts reports a node we don't know about - oh well, ignore it.        
        clusterapi = MockCluster([])
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 0)
       
        #
        # failed node with jetpack. lsf.max_failed_time should be ignored
        clusterapi = MockCluster([self._node("Failed", 4 * 3600 - 10, "10.0.0.4")])
        clusterapi.provider_config.set("lsf.max_failed_time", 100)
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 0)
        
        #
        # failed node with jetpack. lsf.max_failed_time should be ignored
        clusterapi = MockCluster([self._node("Failed", 4 * 3600 + 10, "10.0.0.4")])
        clusterapi.provider_config.set("lsf.max_failed_time", 100)
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer)
        self.assertEquals(len(machines), 1)
        self.assertEquals(machines.pop(0)["ip"], "10.0.0.4")
        
        #
        # failed node without jetpack. lsf.max_failed_time should be respected
        clusterapi = MockCluster([self._node("Failed", 101, "10.0.0.4")])
        clusterapi._nodes[0]["InstallJetpack"] = False
        machines = reaper.reap(clusterapi, subprocess, hostnamer, writer, max_failed_time=100)
        self.assertEquals(len(machines), 1)
        self.assertEquals(machines.pop(0)["ip"], "10.0.0.4")
        

if __name__ == '__main__':
    unittest.main()