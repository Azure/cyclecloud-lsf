import json
import cyclecli
import sys
import os
import random


class Cluster:
    
    def __init__(self, cluster_name, jetpack_config=None):
        self.cluster_name = cluster_name
        if jetpack_config is None:
            import jetpack
            self.jetpack_config = jetpack.config
        else:
            self.jetpack_config = jetpack_config
    
    def nodearrays(self):
        '''pprint.pprint(json.dumps(json.loads(dougs_example)))'''
        test_name = os.getenv("TEST_CASE_NAME")
        if test_name:
            return TEST_CASES[test_name]
        return self.get("/nodearrays?cluster=%s" % self.cluster_name)

    def add_nodes(self, request):
        return self.post("/nodes/create?cluster=%s" % self.cluster_name, json=request)
    
    def nodes(self, **kwattrs):
        exprs = []
        for attr, value in kwattrs.iteritems():
            if isinstance(value, list) or isinstance(value, set):
                expr = '%s in {%s}' % (attr, ",".join(['"%s"' % x for x in value]))
            elif isinstance(value, basestring):
                expr = '%s=="%s"' % (attr, value)
            exprs.append(expr)
        filter_expr = "&&".join(exprs)
        return self.get("/node/searchtmp", Filter=filter_expr)
    
    def terminate(self, node_ids):
        fexpr = 'NodeId in {%s}' % ",".join(['"%s"' % x for x in node_ids])
        try:
            return self.post("/cloud/actions/terminate_node/%s?filter=%s" % (self.cluster_name, fexpr))
        except Exception as e:
            if "No nodes were found matching your query" in str(e):
                return
            raise

    def _session(self):
        try:
            config = {"verify_certificates": False,
                      "username": self.jetpack_config.get("cyclecloud.config.username"),
                      "password": self.jetpack_config.get("cyclecloud.config.password"),
                      "cycleserver": {
                          "timeout": 60
                      }
            }
            return self.jetpack_config.get("cyclecloud.config.web_server"), cyclecli.get_session(config=config)
        except ImportError:
            raise
        
    def post(self, url, data=None, json=None, **kwargs):
        root_url, session = self._session()
        response = session.post(root_url + url, data, json, **kwargs)
        if response.status_code != 200:
            raise ValueError(response.content)
        
    def get(self, url, **params):
        root_url, session = self._session()
        response = session.get(root_url + url, params=params)
        if response.status_code != 200:
            raise ValueError(response.content)
        return json.loads(response.content)


TEST_CASES = {
    "Default": 
        {'maxCoreCount': 10,
         'nodeArrays': [{'buckets': [{'maxCount': 2,
                                      'overrides': {'MachineType': 'Standard_D3_v2'}},
                                     {'maxCoreCount': 6,
                                      'overrides': {'MachineType': 'Standard_D2_v2'}}],
                         'dimensions': ['MachineType'],
                         'machines': {'Standard_D2_v2': {'CoreCount': 2,
                                                         'Location': 'southeastus',
                                                         'Memory': 7168,
                                                         "Priority": random.choice([1, 10]),
                                                         'hasCapacity': True,
                                                         'Name': 'Standard_D2_v2'},
                                      'Standard_D3_v2': {'CoreCount': 4,
                                                         'Location': 'southeastus',
                                                         'Memory': 14336,
                                                         "Priority": random.choice([1, 10]),
                                                         'hasCapacity': True,
                                                         'Name': 'Standard_D3_v2'}},
                         'nodeArray': {'AdType': 'Cloud.Node',
                                       'ClusterName': '%s',
                                       'Custom': 'value',
                                       'IsArray': True,
                                       'MachineType': ['Standard_D3_v2',
                                                       'Standard_D2_v2'],
                                       'Name': 'execute'},
                         'templateName': 'execute'}]},
    "UnavailableVM":
        {'maxCoreCount': 10,
         'nodeArrays': [{'buckets': [{'maxCount': 1,
                                      'overrides': {'MachineType': 'Standard_NC6s_v2'}},
                                     {'maxCoreCount': 2,
                                      'overrides': {'MachineType': 'Standard_D2_v2'}}],
                         'dimensions': ['MachineType'],
                         'machines': {'Standard_D2_v2': {'CoreCount': 2,
                                                         'Location': 'southeastus',
                                                         'Memory': 7168,
                                                         "Priority": random.choice([1, 10]),
                                                         'hasCapacity': True,
                                                         'Name': 'Standard_D2_v2'},
                                      'Standard_NC6s_v2': {'CoreCount': 2,
                                                         'Location': 'southeastus',
                                                         "Priority": random.choice([1, 10]),
                                                         'hasCapacity': True,
                                                         'Memory': 7168,
                                                         'Name': 'Standard_NC6s_v2'}},
                         'nodeArray': {'AdType': 'Cloud.Node',
                                       'ClusterName': '%s',
                                       'Custom': 'value',
                                       'IsArray': True,
                                       'MachineType': ['Standard_NC6s_v2',
                                                       'Standard_D2_v2'],
                                       'Name': 'execute'},
                         'templateName': 'execute'}]},
        "Capacity":  # request 6 cores, should be able to figure this out.
            {'maxCoreCount': 10,
             'nodeArrays': [{'buckets': [{'maxCount': 3,
                                          'overrides': {'MachineType': 'Standard_D3_v2'}},
                                         {'maxCoreCount': 6,
                                          'overrides': {'MachineType': 'Standard_D2_v2'}}],
                             'dimensions': ['MachineType'],
                             'machines': {'Standard_D2_v2': {'CoreCount': 2,
                                                             'Location': 'southeastus',
                                                             'Memory': 7168,
                                                             "Priority": random.choice([1, 10]),
                                                             'Name': 'Standard_D2_v2'},
                                          'Standard_D3_v2': {'CoreCount': 4,
                                                             'Location': 'southeastus',
                                                             'Memory': 14336,
                                                             "Priority": random.choice([1, 10]),
                                                             'Name': 'Standard_D3_v2'}},
                             'nodeArray': {'AdType': 'Cloud.Node',
                                           'ClusterName': '%s',
                                           'Custom': 'value',
                                           'IsArray': True,
                                           'MachineType': ['Standard_D3_v2',
                                                           'Standard_D2_v2'],
                                           'Name': 'execute'},
                             'templateName': 'execute'}]},
}

if __name__ == "__main__":
    try:
        # import jetpack
        # jetpack.util.init_logging = lambda *_args, **_kwargs: 0
        jetpack_config = {"cyclecloud.config.username": "admin",
                          "cyclecloud.config.password": "P@ssw0rd",
                          "cyclecloud.config.web_server": "https://localhost:8444"
                          }
        sys.argv[1] = "terminate"
        sys.argv.append("")

#         sys.argv[1] = "add_node"
#         input_json = {'sets': [{'count': 1,
#                                 'template': "execute",
#                                 'overrides': {'MachineType': "Standard_D2_v2",
#                                              'RequestId': "req-123",
#                                              'Configuration': {"custom": "user-data"},
#                                              }}]}
        cluster = Cluster("ryhamel-lsf", jetpack_config)
        if sys.argv[1] == "nodearrays":
            json.dump(cluster.nodearrays(), sys.stdout, indent=2)
        elif sys.argv[1] == "nodes":
            json.dump(cluster.nodes(RequestId="req-123"), sys.stdout, indent=2) 
        elif sys.argv[1] == "add_node":
            json.dump(cluster.add_nodes(input_json), sys.stdout, indent=2)
        elif sys.argv[1] == "terminate": 
            json.dump(cluster.terminate(["f65e4f508f2eb06c4455e6fbf96ff9a3"]), sys.stdout, indent=2)
        else:
            print "huh?"
    except ImportError as e:
        print "no jetpack"
        raise
