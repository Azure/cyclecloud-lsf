from copy import deepcopy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import cyclecloud_provider
from lsf import RequestStates, MachineStates, MachineResults
import test_json_source_helper
from util import JsonStore
import util


MACHINE_TYPES = {
    "A4": {"Name": "A4", "vcpuCount": 4, "memory": 1., "Location": "ukwest", "Quota": 10},
    "A8": {"Name": "A8", "vcpuCount": 8, "memory": 2., "Location": "ukwest", "Quota": 20}
}


class MockClock:
    
    def __init__(self, now):
        self.now = now
        
    def __call__(self):
        return self.now
    
    
class MockHostnamer:
    
    def hostname(self, private_ip_address):
        return "ip-" + private_ip_address.replace(".", "-")
    

class MockCluster:
    def __init__(self, nodearrays):
        self._nodearrays = nodearrays
        self._nodearrays["nodearrays"].append({"name": "execute",
                                               "nodearray": {"Configuration": {"run_list": ["recipe[lsf::master]"]}}})
        # template -> requestI
        self._nodes = {}
        self.raise_during_termination = False
        self.raise_during_add_nodes = False

    def status(self):
        return self._nodearrays

    def add_nodes(self, request_all):
        '''
                self.cluster.add_node({'Name': nodearray_name,
                                'TargetCount': machine_count,
                                'MachineType': machine_type,
                                "RequestId": request_id,
                                "Configuration": {"lsf": {"user_data": json.dumps(user_data)}}
                                })
        '''
        if self.raise_during_add_nodes:
            raise RuntimeError("raise_during_add_nodes")
        request = request_all["sets"][0]
        nodearray = request["nodearray"]
        request_id = request_all["requestId"]
        count = request["count"]
        machine_type = request["definition"]["machineType"]
        
        if nodearray not in self._nodes:
            self._nodes[nodearray] = []
            
        node_list = self._nodes[nodearray]

        for i in range(count):
            node_index = len(node_list) + i + 1
        
            node_list.append({
                "Name": "%s-%d" % (nodearray, node_index),
                "NodeId": "%s-%d_id" % (nodearray, node_index),
                "RequestId": request_id,
                "machineType": MACHINE_TYPES[machine_type],
                "Status": "Allocating",
                "TargetState": "Started"
            })
            
    def nodes(self, request_ids=[]):
        ret = {}
        
        for request_id in request_ids:
            ret[request_id] = {"nodes": []}
            
        for node in self.inodes(RequestId=request_ids):
            ret[node["RequestId"]]["nodes"].append(node)
        return ret
            
    def inodes(self, **attrs):
        '''
        Just yield each node that matches the attrs specified. If the value is a 
        list or set, use 'in' instead of ==
        '''
        ret = {}
        
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
                        ret[key] = node
                        yield node
        return list(_yield_nodes(**attrs))
    
    def terminate(self, node_ids, unused):
        if self.raise_during_termination:
            raise RuntimeError("raise_during_termination")
        
        for node in self.nodes():
            if node.get("NodeId") in node_ids:
                node["Status"] = "TerminationPreparation"
                node["TargetState"] = "Terminated"
                
                
class RequestsStoreInMem:
    
    def __init__(self, requests=None):
        self.requests = {} if requests is None else requests
        
    def read(self):
        return self.requests
    
    def __enter__(self):
        return self.requests
    
    def __exit__(self, *args):
        pass
    
    
def json_writer(data, debug_output=False):
    return data
            
            
class Test(unittest.TestCase):

    def test_simple_lifecycle(self):
        provider = self._new_provider()
        provider.cluster._nodearrays["nodearrays"][0]["buckets"].pop(1)
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(1, len(templates))
        self.assertEquals("executea4", templates[0]["templateId"])
        self.assertEquals(["Numeric", 4], templates[0]["attributes"]["ncores"])
        self.assertEquals(["Numeric", 4], templates[0]["attributes"]["ncpus"])
        
        provider.cluster._nodearrays["nodearrays"][0]["buckets"].append({"maxCount": 2, "definition": {"machineType": "A8"}, "virtualMachine": MACHINE_TYPES["A8"]})
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(2, len(templates))
        a4 = [t for t in templates if t["templateId"] == "executea4"][0]
        a8 = [t for t in templates if t["templateId"] == "executea8"][0]
        
        self.assertEquals(["Numeric", 4], a4["attributes"]["ncores"])
        self.assertEquals(["Numeric", 4], a4["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 1024], a4["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a4["attributes"]["type"])
        
        self.assertEquals(["Numeric", 8], a8["attributes"]["ncores"])
        self.assertEquals(["Numeric", 8], a8["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 2048], a8["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a8["attributes"]["type"])
        
        request = provider.create_machines(self._make_request("executea4", 1))
        
        def run_test(node_status="Allocation", node_target_state="Started", expected_machines=1, instance={"InstanceId": "i-123", "PrivateIp": "10.0.0.1"},
                     expected_request_status=RequestStates.running, expected_node_status=None,
                     expected_machine_status=MachineStates.building, expected_machine_result=MachineResults.executing,
                     node_status_message=None, status_type="create"):
            if expected_node_status is None:
                expected_node_status = node_status
                
            mutable_node = provider.cluster.inodes(Name="execute-1")
            mutable_node[0]["State"] = node_status
            mutable_node[0]["TargetState"] = node_target_state
            mutable_node[0]["Instance"] = instance
            mutable_node[0]["InstanceId"] = instance["InstanceId"] if instance else None
            mutable_node[0]["StatusMessage"] = node_status_message
            mutable_node[0]["PrivateIp"] = (instance or {}).get("PrivateIp")
            
            if status_type == "create":
                statuses = provider.status({"requests": [{"requestId": request["requestId"]}]})
            else:
                statuses = provider.status({"requests": [{"requestId": request["requestId"]}]})
                
            request_status_obj = statuses["requests"][0]
            self.assertEquals(expected_request_status, request_status_obj["status"])
            machines = request_status_obj["machines"]
            self.assertEquals(expected_machines, len(machines))
            self.assertEquals(expected_node_status, mutable_node[0]["State"])

            if expected_machines == 0:
                return
            
            for n, m in enumerate(machines):
                if m["privateIpAddress"]:
                    self.assertEquals(MockHostnamer().hostname(m["privateIpAddress"]), m["name"])
                self.assertEquals("execute-%d_id" % (n + 1), m["machineId"])
                self.assertEquals(expected_machine_status, m["status"])
                self.assertEquals(expected_machine_result, m["result"])
            
        # no instanceid == no machines
        run_test(instance=None, expected_machines=0)

        # has an instance
        run_test(expected_machines=1)
        
        # has an instance, but Failed
        run_test(expected_machines=1, node_status="Failed", node_status_message="fail for tests",
                 expected_request_status=RequestStates.complete_with_error,
                 expected_machine_status=MachineStates.error,
                 expected_machine_result=MachineResults.failed)
        
        # node is ready to go
        run_test(node_status="Started", expected_machine_result=MachineResults.succeed, 
                                      expected_machine_status=MachineStates.active,
                                      expected_request_status=RequestStates.complete)
        
        # someone somewhere else changed the target state
        run_test(expected_machines=0, node_status="Off", node_target_state="Off",
                 expected_request_status=RequestStates.complete)
        
    def _new_provider(self, provider_config=util.ProviderConfig({}, {}), UserData=""):
        a4bucket = {"maxCount": 2, "definition": {"machineType": "A4"}, "virtualMachine": MACHINE_TYPES["A4"]}
        a8bucket = {"maxCoreCount": 24, "definition": {"machineType": "A8"}, "virtualMachine": MACHINE_TYPES["A8"]}
        cluster = MockCluster({"nodearrays": [{"name": "execute",
                                               "UserData": UserData,
                                               "nodearray": {"machineType": ["a4", "a8"], "Configuration": {"run_list": ["recipe[lsf::slave]"]}},
                                               "buckets": [a4bucket, a8bucket]}]})
        epoch_clock = MockClock((1970, 1, 1, 0, 0, 0))
        hostnamer = MockHostnamer()
        return cyclecloud_provider.CycleCloudProvider(provider_config, cluster, hostnamer, json_writer, RequestsStoreInMem(), RequestsStoreInMem(), epoch_clock)
    
    def _make_request(self, template_id, machine_count, rc_account="default", user_data={}):
        return {"user_data": user_data,
               "rc_account": rc_account,
               "template": {"templateId": template_id,
                            "machineCount": machine_count
                }
            }
        
    def test_terminate(self):
        provider = self._new_provider()
        term_requests = provider.terminate_json
        term_response = provider.terminate_machines({"machines": [{"name": "host-123", "machineId": "id-123"}]})
        
        self.assertEquals(term_response["status"], "complete")
        self.assertTrue(term_response["requestId"] in term_requests.requests)
        self.assertEquals({"id-123": "host-123"}, term_requests.requests[term_response["requestId"]]["machines"])
        
        status_response = provider.status({"requests": [{"requestId": term_response["requestId"]}]})
        self.assertEquals(1, len(status_response["requests"]))
        self.assertEquals(1, len(status_response["requests"][0]["machines"]))
        
        status_response = provider.status({"requests": [{"requestId": "missing"}]})
        self.assertEquals({'status': 'complete', 'requests': [{'status': 'complete', 'message': '', 'requestId': 'missing', 'machines': []}]}, status_response)
        
        status_response = provider.status({"requests": [{"requestId": "delete-missing"}]})
        self.assertEquals({'status': 'running', 'requests': [{'status': 'running', "message": "Unknown termination request id.", 'requestId': 'delete-missing', 'machines': []}]}, status_response)
        
    def test_terminate_error(self):
        provider = self._new_provider()
        term_response = provider.terminate_machines({"machines": [{"name": "host-123", "machineId": "id-123"}]})
        self.assertEquals(term_response["status"], RequestStates.complete)
        
        # if it raises an exception, don't mark the request id as successful.
        provider.cluster.raise_during_termination = True
        term_response = provider.terminate_machines({"machines": [{"name": "host-123", "machineId": "id-123"}]})
        self.assertEquals(RequestStates.running, term_response["status"])
        failed_request_id = term_response["requestId"]
        self.assertNotEquals(True, provider.terminate_json.read()[term_response["requestId"]].get("terminated"))
        
        # if it raises an exception, don't mark the request id as successful.
        provider.cluster.raise_during_termination = False
        term_response = provider.terminate_machines({"machines": [{"name": "host-123", "machineId": "id-123"}]})
        self.assertEquals(RequestStates.complete, term_response["status"])
        self.assertEquals(True, provider.terminate_json.read()[term_response["requestId"]].get("terminated"))
        
        provider.status({"requests": [{"requestId": failed_request_id}]})
        self.assertEquals(True, provider.terminate_json.read()[failed_request_id].get("terminated"))
        
    def test_json_store_lock(self):
        json_store = JsonStore("test.json", "/tmp")
        
        json_store._lock()
        self.assertEquals(101, subprocess.call([sys.executable, test_json_source_helper.__file__, "test.json", "/tmp"]))
        
        json_store._unlock()
        self.assertEquals(0, subprocess.call([sys.executable, test_json_source_helper.__file__, "test.json", "/tmp"]))
        
    def test_templates(self):
        provider = self._new_provider()
        a4bucket, a8bucket = provider.cluster._nodearrays["nodearrays"][0]["buckets"]
        nodearray = {"MaxCoreCount": 100}
        self.assertEquals(2, provider._max_count(nodearray, 4, {"maxCount": 2}))
        self.assertEquals(3, provider._max_count(nodearray, 8, {"maxCoreCount": 24}))
        self.assertEquals(3, provider._max_count(nodearray, 8, {"maxCoreCount": 25}))
        self.assertEquals(3, provider._max_count(nodearray, 8, {"maxCoreCount": 31}))
        self.assertEquals(4, provider._max_count(nodearray, 8, {"maxCoreCount": 32}))
        
        # simple zero conditions
        self.assertEquals(0, provider._max_count(nodearray, 8, {"maxCoreCount": 0}))
        self.assertEquals(0, provider._max_count(nodearray, 8, {"maxCount": 0}))
        
        # error conditions return -1
        nodearray = {}
        self.assertEquals(-1, provider._max_count(nodearray, -100, {"maxCoreCount": 32}))
        self.assertEquals(-1, provider._max_count(nodearray, -100, {"maxCount": 32}))
        self.assertEquals(-1, provider._max_count(nodearray, 4, {}))
        self.assertEquals(-1, provider._max_count(nodearray, 4, {"maxCount": -100}))
        self.assertEquals(-1, provider._max_count(nodearray, 4, {"maxCoreCount": -100}))
        
        a4bucket["maxCount"] = 0
        a8bucket["maxCoreCount"] = 0  # we can _never_ return an empty list
        self.assertEquals(cyclecloud_provider.PLACEHOLDER_TEMPLATE, provider.templates()["templates"][0])
        
        a8bucket["maxCoreCount"] = 24
        self.assertEquals(3, provider.templates()["templates"][-1]["maxNumber"])
        a8bucket["maxCoreCount"] = 0
        
        a4bucket["maxCount"] = 100
        self.assertEquals(100, provider.templates()["templates"][0]["maxNumber"])
        
    def test_errors(self):
        provider = self._new_provider()
        provider.cluster.raise_during_add_nodes = True
        provider.templates()
        response = provider.create_machines(self._make_request("executea4", 1))
        self.assertEquals('Azure CycleCloud experienced an error, though it may have succeeded: raise_during_add_nodes', response["message"])
        self.assertEquals(RequestStates.running, response["status"])
        self.assertNotEquals(None, response.get("requestId"))
        
        provider.cluster.raise_during_termination = True
        term_response = provider.terminate_machines({"machines": [{"machineId": "mach123", "name": "n-1-123"}]})
        self.assertEquals(RequestStates.running, term_response["status"])
                                                     
    def test_missing_template_in_request(self):
        provider = self._new_provider()
        provider.templates_json.requests.clear()
        request = provider.create_machines(self._make_request("executea4", 1))
        self.assertEquals(RequestStates.complete_with_error, request["status"])
        
    def test_expired_terminations(self):
        provider = self._new_provider()
        term_response = provider.terminate_machines({"machines": [{"machineId": "id-123", "name": "e-1-123"},
                                                                  {"machineId": "id-124", "name": "e-2-234"}]})
        self.assertEquals(RequestStates.complete, term_response["status"])
        stat_response = provider.status({"requests": [{"requestId": term_response["requestId"]}]})
        self.assertEquals(RequestStates.complete, stat_response["requests"][0]["status"])
        self.assertIn(term_response["requestId"], provider.terminate_json.read())
        
        # expires after 2 hours, so this is just shy of 2 hours
        provider.clock.now = (1970, 1, 1, 1.99, 0, 0)
        
        expired_request = term_response["requestId"]
        
        term_response = provider.terminate_machines({"machines": [{"machineId": "id-234", "name": "n-1-123"}]})
        stat_response = provider.status({"requests": [{"requestId": term_response["requestId"]}]})
        self.assertEquals(RequestStates.complete, stat_response["requests"][0]["status"])
        self.assertIn(expired_request, provider.terminate_json.read())
        
        # just over 2 hours, it will be gone.
        provider.clock.now = (1970, 1, 1, 2.01, 0, 0)
        stat_response = provider.status({"requests": [{"requestId": term_response["requestId"]}]})
        self.assertNotIn(expired_request, provider.terminate_json.read())
        
    def test_disable_but_do_not_delete_missing_buckets(self):
        provider = self._new_provider()
        templates = provider.templates()["templates"]
        
        def _maxNumber(name):
            ret = [t for t in templates if t["templateId"] == name]
            self.assertEquals(1, len(ret))
            return ret[0]["maxNumber"]
        
        self.assertTrue(_maxNumber("executea4") > 0)
        self.assertTrue(_maxNumber("executea8") > 0)
        
        provider.cluster._nodearrays["nodearrays"][0]["buckets"] = [{"maxCount": 2, "definition": {"machineType": "A4"}, "virtualMachine": MACHINE_TYPES["A4"]}]
        templates = provider.templates()["templates"]
        
        self.assertTrue(_maxNumber("executea4") > 0)
        self.assertTrue(_maxNumber("executea8") == 0)
        
    def test_override_template(self):
        provider = self._new_provider()
        other_array = deepcopy(provider.cluster._nodearrays["nodearrays"][0])
        other_array["name"] = "other"
        provider.cluster._nodearrays["nodearrays"].append(other_array)
        
        def any_template(template_name):
            return [x for x in provider.templates()["templates"] if x["templateId"].startswith(template_name)][0]
        
        provider.config.set("templates.default.attributes.custom", ["String", "custom_default_value"])
        provider.config.set("templates.execute.attributes.custom", ["String", "custom_override_value"])
        provider.config.set("templates.execute.attributes.custom2", ["String", "custom_value2"])
        provider.config.set("templates.other.maxNumber", 0)
        
        # a4 overrides the default and has custom2 defined as well
        attributes = any_template("execute")["attributes"]
        self.assertEquals(["String", "custom_override_value"], attributes["custom"])
        self.assertEquals(["String", "custom_value2"], attributes["custom2"])
        self.assertEquals(["Numeric", 1. * 1024], attributes["mem"])
        
        # a8 only has the default
        attributes = any_template("other")["attributes"]
        self.assertEquals(["String", "custom_default_value"], attributes["custom"])
        self.assertNotIn("custom2", attributes)
        self.assertEquals(0, any_template("other")["maxNumber"])
        
    def test_invalid_template(self):
        provider = self._new_provider()
        response = provider.create_machines(self._make_request("nonsense", 1))
        self.assertEquals(RequestStates.complete_with_error, response["status"])
        
    def test_provider_config_from_env(self):
        tempdir = tempfile.mkdtemp()
        confdir = os.path.join(tempdir, "conf")
        os.makedirs(confdir)
        try:
            with open(os.path.join(confdir, "azureccprov_config.json"), "w") as fw:
                json.dump({}, fw)
                
            with open(os.path.join(confdir, "azureccprov_templates.json"), "w") as fw:
                json.dump({"templates": 
                           [{"templateId": "default", "attributes": {"custom": ["String", "VALUE"]}}]}, fw)
            
            config, _logger, _fine = util.provider_config_from_environment(tempdir)
            provider = self._new_provider(provider_config=config)
            for template in provider.templates()["templates"]:
                self.assertIn(template["templateId"], ["executea4", "executea8"])
                assert "custom" in template["attributes"]
                self.assertEquals(["String", "VALUE"], template["attributes"]["custom"])
            
        except Exception:
            shutil.rmtree(tempdir, ignore_errors=True)
            raise
        
    def test_custom_env(self):
        config = util.ProviderConfig({}, {})
        provider = self._new_provider(config)
        
        config.set("templates.default.UserData", "abc=123;def=1==1")
        self.assertEquals({"abc": "123", "def": "1==1"}, provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env"])
        self.assertEquals("abc def", provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env_names"])
        
        config.set("templates.default.UserData", "abc=123;def=1==1;")
        self.assertEquals({"abc": "123", "def": "1==1"}, provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env"])
        self.assertEquals("abc def", provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env_names"])
        
        config.set("templates.default.UserData", "abc=123;def=1==1;bad_form")
        
        self.assertEquals({"abc": "123", "def": "1==1"}, provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env"])
        self.assertEquals("abc def", provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env_names"])
        
        config.set("templates.default.UserData", "abc=123;def=1==1;good_form=234;bad_form_123")
        self.assertEquals({"abc": "123", "def": "1==1", "good_form": "234"}, provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env"])
        self.assertEquals("abc def good_form", provider.templates()["templates"][0]["UserData"]["lsf"]["custom_env_names"])
        
        def assert_no_user_data():
            templates = provider.templates()
            self.assertNotIn("custom_env", templates["templates"][0]["UserData"]["lsf"])
            self.assertNotIn("custom_env_names", templates["templates"][0]["UserData"]["lsf"])
            
        config.set("templates.default.UserData", ";")
        assert_no_user_data()
        
        config.set("templates.default.UserData", None)
        assert_no_user_data()
        
        config.set("templates.default.UserData", "all;around;bad")
        assert_no_user_data()


if __name__ == "__main__":
    unittest.main()
