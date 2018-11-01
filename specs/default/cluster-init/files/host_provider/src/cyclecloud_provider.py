import calendar
import json
import os
import pprint
import sys
import uuid

from lsf import RequestStates, MachineStates, MachineResults
import new_api
from util import JsonStore, failureresponse
import util


logger = util.init_logging()


PLACEHOLDER_TEMPLATE = {"templateId": "exceptionPlaceholder", 
                        "maxNumber": 1,
                        "attributes": {
                            "mem": ["Numeric", 1024],
                            "ncpus": ["Numeric", 1],
                            "ncores": ["Numeric", 1]
                            }
                        }


class CycleCloudProvider:
    
    def __init__(self, config, cluster, json_writer, terminate_requests, templates, clock):
        self.config = config
        self.cluster = cluster
        self.json_writer = json_writer
        self.terminate_json = terminate_requests
        self.templates_json = templates
        self.exit_code = 0
        self.clock = clock
        self.termination_timeout = float(self.config.get("termination_retirement", 7200))
        self.node_request_timeouts = float(self.config.get("machine_request_retirement", 7200))

    def _escape_id(self, name):
        return name.lower().replace("_", "")
    
    # If we return an empty list or templates with 0 hosts, it removes us forever and ever more, so _always_
    # return at least one machine.
    @failureresponse({"templates": [PLACEHOLDER_TEMPLATE], "status": RequestStates.complete_with_error})
    def templates(self):
        """
        input (ignored):
        []
        
        output:
        {'templates': [{'attributes': {'azurehost': ['Boolean', '1'],
                               'mem': ['Numeric', '2048'],
                               'ncores': ['Numeric', '4'],
                               'ncpus': ['Numeric', '4'],
                               'type': ['String', 'X86_64'],
                               'zone': ['String', 'southeastus']},
                'instanceTags': 'group=project1',
                'maxNumber': 10,
                'pgrpName': None,
                'priority': 0,
                'templateId': 'execute0'},
               {'attributes': {'azurehost': ['Boolean', '1'],
                               'mem': ['Numeric', '4096'],
                               'ncores': ['Numeric', '8'],
                               'ncpus': ['Numeric', '8'],
                               'type': ['String', 'X86_64'],
                               'zone': ['String', 'southeastus']},
                'instanceTags': 'group=project1',
                'maxNumber': 10,
                'pgrpName': None,
                'priority': 0,
                'templateId': 'execute1'}]}
        """
        
        prior_templates = self.templates_json.read()
        hash_code_before = json.dumps(prior_templates)
        
        at_least_one_available_bucket = False
        
        with self.templates_json as templates_store:
            
            # returns Cloud.Node records joined on MachineType - the array node only
            response = self.cluster.nodearrays()

            nodearrays = response["nodeArrays"]
            
            currently_available_templates = set()
            
            default_priority = len(nodearrays) * 10
            
            for nodearray_root in nodearrays:
                nodearray = nodearray_root.get("nodeArray")
                if "recipe[lsf::master]" in nodearray.get("Configuration", {}).get("run_list", []):
                    continue
                
                dimensions = nodearray_root.get("dimensions", ["MachineType"])
                assert nodearray.get("dimensions", ["MachineType"]) == ["MachineType"], "Unsupported dimensions at this time: %s" % dimensions
                
                for bucket in nodearray_root.get("buckets"):
                    machine_type_name = bucket["overrides"]["MachineType"]
                    machine_type = response["machineTypes"][machine_type_name]
                    
                    # LSF hates special characters
                    template_id = "%s%s" % (nodearray_root.get("templateName"), machine_type_name)
                    template_id = self._escape_id(template_id)
                    currently_available_templates.add(template_id)
                    
                    max_count = self._max_count(nodearray, machine_type.get("CoreCount"), bucket)
                    
                    at_least_one_available_bucket = at_least_one_available_bucket or max_count > 0
                    memory = machine_type.get("Memory")
                    if memory <= 1024:
                        memory = memory * 1024
                        
                    record = {
                        "maxNumber": max_count,
                        "templateId": template_id,
                        "priority": nodearray.get("Priority", default_priority),
                        "attributes": {
                            "zone": ["String", nodearray.get("Region")],
                            "mem": ["Numeric", memory],
                            "ncpus": ["Numeric", machine_type.get("CoreCount")],
                            "ncores": ["Numeric", machine_type.get("CoreCount")],
                            "azurehost": ["Boolean", "1"],
                            "type": ["String", "X86_64"],
                            "machinetype": ["String", machine_type_name],
                            "nodearray": ["String", nodearray_root.get("templateName")]
                        }
                    }
                    templates_store[template_id] = record
                    default_priority = default_priority - 10
            
            # for templates that are no longer available, advertise them but set maxNumber = 0
            for lsf_template in templates_store.values():
                if lsf_template["templateId"] not in currently_available_templates:
                    lsf_template["maxNumber"] = 0
           
        new_templates = self.templates_json.read()
        hash_code_after = json.dumps(new_templates)
        if hash_code_after != hash_code_before:
            logger.warn("Templates have changed - %s" % (pprint.pformat(new_templates)))

        lsf_templates = list(new_templates.values())
        lsf_templates = sorted(lsf_templates, key=lambda x: -x["maxNumber"])
        
        # Note: we aren't going to store this, so it will naturally appear as an error during allocation.
        if not at_least_one_available_bucket:
            lsf_templates.insert(0, PLACEHOLDER_TEMPLATE)
        
        return self.json_writer({"templates": lsf_templates}, debug_output=False)
    
    def _max_count(self, nodearray, machine_cores, bucket):
        if machine_cores < 0:
            logger.error("Invalid number of machine cores - %s" % machine_cores)
            return -1
        
        max_count = bucket.get("maxCount")
        
        if max_count is not None:
            return max(-1, max_count)
        
        max_core_count = bucket.get("maxCoreCount")
        if max_core_count is None:
            if nodearray.get("MaxCoreCount") is None:
                logger.error("Need to define either maxCount or maxCoreCount! %s" % pprint.pformat(nodearray))
                return -1
            max_core_count = nodearray.get("MaxCoreCount")
        
        max_core_count = max(-1, max_core_count)
        
        return max_core_count / machine_cores
    
    @failureresponse({"requests": [], "status": RequestStates.running})
    def create_machines(self, input_json):
        """
        input:
        {'rc_account': 'default',
         'template': {'machineCount': 1, 'templateId': 'execute0'},
         'user_data': {}}

        output:
        {'message': 'Request VM from Azure CycleCloud successful.',
         'requestId': 'req-123'}
        """
        request_id = str(uuid.uuid4())
        try:
            template_store = self.templates_json.read()
        
            # same as nodearrays - Cloud.Node joined with MachineType
            template_id = input_json["template"]["templateId"]
            template = template_store.get(template_id)
            
            if not template:
                available_templates = template_store.keys()
                return self.json_writer({"requestId": request_id, "status": RequestStates.complete_with_error, 
                                        "message": "Unknown templateId %s. Available %s" % (template_id, available_templates)})
                
            machine_count = input_json["template"]["machineCount"]
            
            def _get(name):
                return template["attributes"].get(name, [None, None])[1]
            
            # RequestId may or may not be special. Add a subdict most likely.
            self.cluster.add_nodes({'sets': [{'count': machine_count,
                                               'overrides': {'MachineType': _get("machinetype"),
                                                             'RequestId': request_id},
                                              'template': _get("nodearray")}]})
            
            return self.json_writer({"requestId": request_id, "status": RequestStates.running,
                                     "message": "Request instances success from Azure CycleCloud."})
        except Exception as e:
            logger.exception("Azure CycleCloud experienced an error, though it may have succeeded: %s" % str(e))
            return self.json_writer({"requestId": request_id, "status": RequestStates.running,
                                     "message": "Azure CycleCloud experienced an error, though it may have succeeded: %s" % str(e)})
            
    @failureresponse({"requests": [], "status": RequestStates.running})
    def create_status(self, input_json):
        """
        input:
        {'requests': [{'requestId': 'req-123'}, {'requestId': 'req-234'}]}

    
        output:
        {'message': '',
         'requests': [{'machines': [{'launchtime': 1516131665,
                                     'machineId': 'id-123',
                                     'message': '',
                                     'name': 'execute-5',
                                     'privateIpAddress': '10.0.1.23',
                                     'result': 'succeed',
                                     'status': 'running'}],
                       'message': '',
                       'requestId': 'req-123',
                       'status': 'complete'}],
         'status': 'complete'}

        """
        request_status = RequestStates.complete
        
        request_ids = [r["requestId"] for r in input_json["requests"]]
        
        all_nodes = self.cluster.nodes(RequestId=request_ids)

        message = ""
        
        nodes_by_request_id = {}
        for request in input_json["requests"]:
            nodes_by_request_id[request["requestId"]] = []
        
        for node in all_nodes:
            req_id = node["RequestId"]
            nodes_by_request_id[req_id].append(node)
        
        response = {"requests": []}
            
        for request_id, requested_nodes in nodes_by_request_id.iteritems():
            if not requested_nodes:
                # nothing to do.
                logger.warn("No nodes found for request id %s." % request_id)
            
            machines = []
            request = {"requestId": request_id,
                        "machines": machines}
            
            response["requests"].append(request)
            
            for node in requested_nodes:
                    
                # for new nodes, completion is Ready. For "released" nodes, as long as
                # the node has begun terminated etc, we can just say success.
                node_status = node.get("Status")
                node_target_state = node.get("TargetState", "Started")
                
                machine_status = MachineStates.active
                
                if node_target_state != "Started":
                    continue
                
                elif node_status in ["Unavailable", "Failed"]:
                    machine_result = MachineResults.failed
                    machine_status = MachineStates.error
                    if request_status != RequestStates.running:
                        message = node.get("StatusMessage", "Unknown error.")
                        request_status = RequestStates.complete_with_error
        
                elif not node.get("InstanceId"):
                    request_status = RequestStates.running
                    continue
                
                elif node_status == "Ready":
                    machine_result = MachineResults.succeed
                    machine_status = MachineStates.active
                else:
                    machine_result = MachineResults.executing
                    machine_status = MachineStates.building
                    request_status = RequestStates.running
                
                machine = {
                    "name": node.get("Name"),
                    "status": machine_status,
                    "result": machine_result,
                    "machineId": node.get("NodeId"),
                    # maybe we can add something so we don"t have to expose this
                    # node["PhaseMap"]["Cloud.AwaitBootup"]["StartTime"]["$date"]
                    "launchtime": node.get("LaunchTime"),
                    "privateIpAddress": (node.get("Instance") or {}).get("PrivateIp"),
                    "message": node.get("StatusMessage")
                }
                
                machines.append(machine)
                
            request["status"] = request_status
            request["message"] = message

        return self.json_writer(response)
        
    @failureresponse({"requests": [], "status": RequestStates.running})
    def terminate_status(self, input_json):
        # can transition from complete -> executing or complete -> complete_with_error -> executing
        # executing is a terminal state.
        request_status = RequestStates.complete
        
        response = {"requests": []}
        # needs to be a [] when we return
        with self.terminate_json as terminate_requests:
            
            self._cleanup_expired_requests(terminate_requests, self.termination_timeout)
            
            termination_ids = [r["requestId"] for r in input_json["requests"] if r["requestId"]]
            try:
                node_ids = []
                for termination_id in termination_ids:
                    if termination_id in terminate_requests:
                        termination = terminate_requests[termination_id]
                        if not termination.get("terminated"):
                            node_ids.extend(termination["machines"])
                
                if node_ids:
                    self.cluster.terminate(node_ids)
                    
                for termination_id in termination_ids:
                    if termination_id in terminate_requests:
                        termination = terminate_requests[termination_id]
                        termination["terminated"] = True
            except Exception:
                request_status = RequestStates.running
                logger.exception("Could not terminate nodes with ids %s. Will retry" % (node_ids))
            
            for termination_id in termination_ids:
                machines = []
                request = {"requestId": termination_id,
                        "machines": machines}
            
                response["requests"].append(request)
                
                if termination_id in terminate_requests:
                    termination_request = terminate_requests.get(termination_id)
                    node_names = termination_request.get("machines", [])
                    
                    if not node_names:
                        logger.warn("No machines found for termination request %s. Will retry." % termination_id)
                        request_status = RequestStates.running
                    
                    for node_name in node_names:
                        machines.append({"name": node_name,
                                       "status": MachineStates.deleted,
                                       "result": MachineResults.succeed,
                                       "machineId": node_name})
                else:
                    # we don't recognize this termination request!
                    logger.warn(("Unknown termination request %s. You may intervene manually by updating terminate_nodes.json" + 
                                 " to contain the relevant NodeIds. %s ") % (termination_id, terminate_requests))
                    # set to running so lsf will keep retrying, hopefully, until someone intervenes.
                    request_status = RequestStates.running
                    request["message"] = "Unknown termination request id."

                request["status"] = request_status
        return self.json_writer(response)
        
    def _cleanup_expired_requests(self, requests, retirement):
        now = calendar.timegm(self.clock())
        for req_id in list(requests.keys()):
            try:
                request = requests[req_id]
                request_time = request.get("requestTime", -1)
                
                if request_time < 0:
                    logger.info("Request has no requestTime")
                    request["requestTime"] = request_time = now
                # in case someone puts in a string manuall
                request_time = float(request_time)
                    
                logger.info("Request is %s old vs %s" % ((now - request_time), retirement))
                if (now - request_time) > retirement:
                    logger.info("Found retired request %s" % request)
                    requests.pop(req_id)
                
            except Exception:
                logger.exception("Could not remove stale request %s" % req_id)
                
    @failureresponse({"status": RequestStates.complete_with_error})
    def terminate_machines(self, input_json):
        """
        input:
        {
            "machines":[ {"name": "host-123", "machineId": "id-123"} ]
        }
        
        output:
        {
            "message" : "Delete VM success.",
            "requestId" : "delete-i-123",
            "status": "complete"
        }
        """
        request_id = "delete-%s" % (str(uuid.uuid4()))
        request_id_persisted = False
        try:
            with self.terminate_json as terminations:
                node_ids = [x["machineId"] for x in input_json["machines"]]
                terminations[request_id] = {"id": request_id, "machines": node_ids, "requestTime": calendar.timegm(self.clock())}
            
            request_id_persisted = True
            request_status = RequestStates.complete
            message = "CycleCloud is terminating the VM(s)",

            try:
                self.cluster.terminate(node_ids)
                with self.terminate_json as terminations:
                    terminations[request_id]["terminated"] = True
            except Exception:
                # set to running, we will retry on any status call anyways.
                request_status = RequestStates.running
                message = str(message)
                logger.exception("Could not terminate %s" % node_ids)
            
            return self.json_writer({"message": message,
                                     "requestId": request_id,
                                     "status": request_status
                                     })
        except Exception as e:
            logger.exception(str(e))
            if request_id_persisted:
                return self.json_writer({"status": RequestStates.running, "requestId": request_id})
            return self.json_writer({"status": RequestStates.complete_with_error, "requestId": request_id, "message": str(e)})


def simple_json_writer(data, debug_output=True):  # pragma: no cover
    data_str = json.dumps(data)
    if debug_output:
        logger.debug("Response: %s" % data_str)
    print data_str
    return data


def true_gmt_clock():  # pragma: no cover
    import time
    return time.gmtime()


def main(argv=sys.argv, json_writer=simple_json_writer):  # pragma: no cover
    try:
        
        json_dir = os.getenv('PRO_DATA_DIR', os.getcwd())
        config_file = os.getenv('PRO_CONF_DIR', os.getcwd()) + os.sep + "provider.json"
        config = {}
        if os.path.exists(config_file):
            with open(config_file) as fr:
                config = json.load(fr)
                
        provider_config = util.ProviderConfig(config)
        
        cluster_name = provider_config.get("cyclecloud.cluster.name")
        provider = CycleCloudProvider(provider_config,
                                      new_api.Cluster(cluster_name, provider_config), json_writer,
                                      JsonStore("terminate_requests.json", json_dir),
                                      JsonStore("templates.json", json_dir, formatted=True),
                                      true_gmt_clock)
        cmd, ignore, input_json_path = argv[1:]
        
        with open(input_json_path) as fr:
            input_json = json.load(fr)
        
        logger.info("Arguments - %s %s %s" % (cmd, ignore, json.dumps(input_json)))
                
        if cmd == "templates":
            provider.templates()
        elif cmd == "create_machines":
            provider.create_machines(input_json)
        elif cmd == "status":
            any_request_id = input_json["requests"][0]["requestId"]
            if any_request_id.startswith("delete-"):
                provider.terminate_status(input_json)
            else:
                provider.create_status(input_json)
        elif cmd == "terminate_machines":
            provider.terminate_machines(input_json)
            
    except ImportError as e:
        logger.exception(str(e))
    except Exception as e:
        logger.exception(str(e))


if __name__ == "__main__":
    main()  # pragma: no cover
