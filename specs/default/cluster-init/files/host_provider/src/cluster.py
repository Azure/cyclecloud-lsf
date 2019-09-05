import json

import logging
from urllib import urlencode
from util import chaos_mode


try:
    import cyclecli
except ImportError:
    import cyclecliwrapper as cyclecli
    

class Cluster:
    
    def __init__(self, cluster_name, provider_config, logger=None):
        self.cluster_name = cluster_name
        self.provider_config = provider_config
        self.logger = logger or logging.getLogger()
    
    def status(self):
        '''pprint.pprint(json.dumps(json.loads(dougs_example)))'''
        return self.get("/clusters/%s/status" % self.cluster_name)

    def add_nodes(self, request):
        return json.loads(self.post("/clusters/%s/nodes/create" % self.cluster_name, json=request))
    
    def nodes(self, request_ids):
        responses = {}
        for request_id in request_ids:
            responses[request_id] = self.get("/clusters/%s/nodes" % self.cluster_name, request_id=request_id)
        return responses
    
    def nodes_by_operation_id(self, operation_id):
        if not operation_id:
            raise RuntimeError("You must specify operation id!")
        return self.get("/clusters/%s/nodes?operation=%s" % (self.cluster_name, operation_id))
    
    def shutdown(self, machines, hostnamer):
        if not machines:
            return
        
        id_to_ip = {}
        for machine in machines:
            id_to_ip[machine["machineId"]] = hostnamer.private_ip_address(machine["name"])
        
        response_raw = self.post("/clusters/%s/nodes/shutdown" % self.cluster_name, json={"ids": id_to_ip.keys()})
        response = json.loads(response_raw)
        for node in response["nodes"]:
            id_to_ip.pop(node["id"])
        
        # kludge: work around
        # if LSF has a stale machineId -> hostname mapping, find the existing instance with that ip and kill it
        
        if id_to_ip:
            ips = id_to_ip.values()
            self.logger.warn("Terminating the following nodes by ip address: %s", id_to_ip.keys())
            
            for i in range(0, len(ips), 10):
                subset_ips = ips[i:min(len(ips), i + 10)]
                f = urlencode({"instance-filter": 'PrivateIp in {%s}' % ",".join('"%s"' % x for x in subset_ips)})
                
                try:
                    self.post("/cloud/actions/terminate_node/%s?%s" % (self.cluster_name, f))
                except cyclecli.UserError as e:
                    if "No instances were found matching your query" in unicode(e):
                        return
                    raise
            
    def _session(self):
        config = {"verify_certificates": False,
                  "username": self._get_or_raise("cyclecloud.config.username"),
                  "password": self._get_or_raise("cyclecloud.config.password"),
                  "cycleserver": {
                      "timeout": 60
                  }
        }
        return cyclecli.get_session(config=config)
    
    def _get_or_raise(self, key):
        value = self.provider_config.get(key)
        if not value:
            #  jetpack.config.get will raise a ConfigError above.
            raise cyclecli.ConfigError("Please define key %s in the provider config." % key)
        return value
    
    @chaos_mode
    def post(self, url, data=None, json=None, **kwargs):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        self.logger.debug("POST %s with data %s json %s kwargs %s", root_url + url, data, json, kwargs)
        session = self._session()
        response = session.post(root_url + url, data, json, **kwargs)
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response.content)
        return response.content
    
    @chaos_mode
    def get(self, url, **params):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        self.logger.debug("GET %s with params %s", root_url + url, params)
        session = self._session()
        response = session.get(root_url + url, params=params)
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response.content)
        return json.loads(response.content)
