import json


class Cluster:
    
    def __init__(self, cluster_name):
        self.cluster_name = cluster_name
    
    def nodearrays(self):
        return self.get("/cloud/cluster/nodearray")
    
    def nodearray(self, name):
        return self.get("/cloud/cluster/nodearray", name=name)
    
    def add_node(self, request):
        return self.post("/cloud/cluster/add_node", body=json.dumps(request))
    
    def nodes(self, filter_expr):
        return self.get("/cloud/cluster/node", filter=filter_expr)
    
    def terminate(self, instance_ids):
        return self.post("/cloud/cluster/terminate_node", instance_ids=",".join(instance_ids))

    def post(self, *args, **kwargs):
        pass
        
    def get(self, *args, **kwargs):
        pass