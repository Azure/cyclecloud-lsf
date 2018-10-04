import json
import cyclecli
import sys


class Cluster:
    
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name
    
    def nodearrays(self):
        return {"Name": "execute",
                "MachineType": [{"Name": "Standard_H16",
                                 "CoreCount": 16,
                                 "Memory": 112 * 1024,
                                 "Quota": 2,
                                 "Location": "southeastus"},
                                 {"Name": "Standard_F16",
                                 "CoreCount": 16,
                                 "Quota": 2,
                                 "Memory": 32 * 1024,
                                 "Location": "southeastus"},
                    ]}
    
    def add_node(self, request):
        return self.post("/ryan/add_nodes/%s" % self.cluster_name, json=request)
    
    def nodes(self, filter_expr):
        return self.get("/ryan/nodes/%s" % self.cluster_name, Filter=filter_expr)
    
    def terminate(self, instance_ids):
        return self.post("/ryan/terminate_node/%s" % self.cluster_name, instance_ids=",".join(instance_ids))

    def _session(self):
        try:
            import jetpack
            config = {"verify_certificates": False,
                      "username": jetpack.config.get("cyclecloud.config.username"),
                      "password": jetpack.config.get("cyclecloud.config.password"),
                      "cycleserver": {
                          "timeout": 60
                      }
            }
            return jetpack.config.get("cyclecloud.config.web_server"), cyclecli.get_session(config=config)
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


if __name__ == "__main__":
    try:
        import jetpack
        cluster = Cluster(jetpack.config.get("cyclecloud.cluster.name"))
        if sys.argv[1] == "nodearrays":
            json.dump(cluster.nodearrays(), sys.stdout)
        elif sys.argv[1] == "nodes":
            json.dump(cluster.nodes(sys.argv[2])) 
        elif sys.argv[1] == "add_node":
            json.dump(cluster.add_node(json.load(sys.stdin)))
        elif sys.argv[1] == "terminate": 
            json.dump(cluster.terminate(json.load(sys.stdin)))
        else:
            print "huh?"
    except ImportError as e:
        print "no jetpack"
        raise e
