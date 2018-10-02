import json
import sys
import traceback
import new_api
import uuid


log = open('/tmp/lsfrc.log', 'a')


def simple_json_writer(data):
    data_str = json.dumps(data)
    print >> log, data_str
    print data_str
    return data


class CycleCloudProvider:
    
    def __init__(self, cluster, json_writer=None):
        self.cluster = cluster
        self.json_writer = json_writer

    def templates(self):
        '''
        input (ignored):
        []
        
        output:
        {
            "templates": [
                {
                    "maxNumber": 10, 
                    "instanceTags": "group=project1", 
                    "priority": 0, 
                    "templateId": "execute", 
                    "attributes": {
                        "zone": ["String","southeastus"], 
                        "mem": ["Numeric","8192"], 
                        "ncpus": ["Numeric","4"],
                        "azurehost": ["Boolean","1"], 
                        "ncores": ["Numeric","4"], 
                        "type": ["String","X86_64"]
                    }, 
                    "pgrpName": None
                }
            ]
        }
        '''
        lsf_templates = []
        
        # returns Cloud.Node records joined on MachineType - the array node only
        nodearrays = self.cluster.nodearrays()
        
        for nodearray in nodearrays:
            instance_tags = " ".join(["%s=%s" % (x, y) for x, y in nodearray.get("Tags", {}).iteritems()])
            
            for machine_type in nodearray.get("MachineType"):
                # smuggle machine type with @ in nodearray.
                templateId = "%s@%s" % (nodearray.get("Name"), machine_type.get("Name"))
                
                lsf_templates.append({
                    "maxNumber": machine_type.get("Quota"),
                    "instanceTags": instance_tags,
                    "priority": nodearray.get("Priority"),
                    "templateId": templateId,
                    "attributes": {
                        "zone": ["String", machine_type.get("Location")],
                        "mem": ["Numeric", machine_type.get("Memory")],
                        "ncpus": ["Numeric", max(1, machine_type.get("CoreCount") / 2)],
                        "ncores": ["Numeric", machine_type.get("CoreCount")],
                        "type": ["String", "X86_64"]
                    }
                })
        
        print >> log, "templates"
        return self.json_writer({"templates": lsf_templates})
    
    
    def request(self, input_json):
        '''
        input:
        {
        "user_data": {},
        "rc_account": "default",
        "template":
            {
                "templateId": "execute@Standard_A4",
                "machineCount": 1
            }
        }
        output:
        {
            "message": "Request VM from Azure CycleCloud successful.",
            "requestId":"req-123"
        }
        '''
    
        # same as nodearrays - Cloud.Node joined with MachineType
        nodearray_name, machine_type = input_json["template"]["templateId"].split("@", 1)
        
        machine_count = input_json["template"]["machineCount"]
        
        request_id = str(uuid.uuid4())
        
        # RequestId may or may not be special. Add a subdict most likely.
        user_data = input_json.get("user_data", {})
        self.cluster.add_node({'Name': nodearray_name,
                                'TargetCount': machine_count,
                                'MachineType': machine_type,
                                "RequestId": request_id,
                                "Configuration": {"lsf": {"user_data": json.dumps(user_data)}}
                                })
        return self.json_writer({"requestId": request_id})
    
    
    def status(self, input_json):
        '''
        input:
        {
            "requests": [{"requestId": "req-123"},
                         {"requestId": "req-234"}]
        }
    
        output:
        {
          "requests" : [ {
            "status" : "complete",
            "machines" : [ {
              "machineId" : "id-123",
              "name" : "execute-5",
              "result" : "succeed",
              "status" : "RUNNING",
              "privateIpAddress" : "10.0.1.23",
              "launchtime" : 1516131665,
              "message" : ""
            } ],
            "requestId" : "req-123",
            "message" : ""
          },{
            "status" : "complete",
            "machines" : [ {
              "machineId" : "id-234",
              "name" : "execute-4",
              "result" : "succeed",
              "status" : "OFF",
              "privateIpAddress" : "10.0.2.34",
              "launchtime" : 1516131665,
              "message" : ""
            } ],
            "requestId" : "req-234",
            "message" : ""
          } ]
        }
        '''
        statuses = {} # needs to be a [] when we return
        
        request_ids = [r["requestId"] for r in input_json["requests"]]
        
        filter_expr = 'RequestId in {%s}' % ",".join(['"%s"' % x for x in request_ids])
        nodes = self.cluster.nodes(filter_expr)
        
        # can transition from complete -> executing or complete -> complete_with_error -> executing
        # executing is a terminal state.
        request_status = "complete"
        
        for node in nodes:
            request_id = node["RequestId"] 
            if request_id not in statuses:
                statuses[request_id] = {
                    "machines": []
                }
            # for new nodes, completion is Ready. For 'released' nodes, as long as
            # the node has begun terminated etc, we can just say success.
            node_status = node.get("Status")
            if node_status == "Failed":
                lsf_result = "fail"
    
                if request_status != "executing":
                    request_status = "complete_with_error"
                    
            elif node_status == "Ready" or node.get("TargetState") != "Ready":
                lsf_result = "succeed"
            else:
                lsf_result = "executing"
                request_status = "executing"
                
            machine = {
                # instanceid?
                "name": node["Name"],
                "result": lsf_result,
                "machineId": node.get("InstanceId"),
                # maybe we can add something so we don't have to expose this
                # node["PhaseMap"]["Cloud.AwaitBootup"]["StartTime"]
                "launchtime": node["LaunchTime"],
                "privateIpAddress": node["Instance"]["PrivateIp"],
                "message": node.get("StatusMessage")
                
            }
            
            statuses[request_id]["machines"].append(machine)
            
        return self.json_writer({"requests": list(statuses.iteritems())})
    
    
    def terminate(self, input_json):
        '''
        input:
        {
            "machines":[ {"name": "host-123", "machineId": "id-123"} ]
        }
        
        output:
        {
            "message" : "Delete VM success.",
            "requestId" : "delete-123"
        }
        '''
        instance_ids = [x.get("machineId") for x in input_json["machines"]]
        request_id = str(uuid.uuid4())
        
        # we need a request id to return... but once this completes, 
        # a missing status for the previous nodes might be fine?
        self.cluster.terminate(instance_ids=instance_ids)
        return self.json_writer({
                "message" : "Delete VM success.",
                "requestId" : request_id
                })

if __name__ == "__main__":
    try:
        provider = CycleCloudProvider(new_api.Cluster(), simple_json_writer)
        cmd, ignore, input_json_path = sys.argv[1:]
        with open(input_json_path) as fr:
            input_json = json.load(fr)
        print >> log, cmd, ignore, json.dumps(input_json)
        if cmd == "templates":
            provider.templates()
        elif cmd == "request":
            provider.request(input_json)
        elif cmd == "status":
            provider.status(input_json)
        elif cmd == "terminate":
            provider.terminate(input_json)
    except:
        traceback.print_exc(file=log)
        raise
