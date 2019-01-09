import json

import collections
import logging


try:
    import cyclecli
except ImportError:
    import cyclecliwrapper as cyclecli
    

class Cluster:
    
    def __init__(self, cluster_name, provider_config, logger=None):
        self.cluster_name = cluster_name
        self.provider_config = provider_config
        self.logger = logger or logging.getLogger()
    
    def describe(self):
        '''pprint.pprint(json.dumps(json.loads(dougs_example)))'''
        return self.get("/clusters/%s" % self.cluster_name)

    def add_nodes(self, request):
        return self.post("/nodes/create?cluster=%s" % self.cluster_name, json=request)
    
    def nodes(self, request_ids):
        responses = {}
        for request_id in request_ids:
            responses[request_id] = self.get("/nodes", request_id=request_id)
        return responses
    
    def terminate(self, node_ids):
        self.post("/nodes/terminate/%s" % self.cluster_name, json={"ids": node_ids})
        
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
    
    def post(self, url, data=None, json=None, **kwargs):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        self.logger.debug("POST %s with data %s json %s kwargs %s", root_url + url, data, json, kwargs)
        session = self._session()
        response = session.post(root_url + url, data, json, **kwargs)
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response.content)
        
    def get(self, url, **params):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        self.logger.debug("GET %s with params %s", root_url + url, params)
        session = self._session()
        response = session.get(root_url + url, params=params)
        if response.status_code < 200 or response.status_code > 299:
            raise ValueError(response.content, object_pairs_hook=collections.OrderedDict)
        return json.loads(response.content)
