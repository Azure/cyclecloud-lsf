import json

import collections


try:
    import cyclecli
except ImportError:
    import cyclecliwrapper as cyclecli
    

class Cluster:
    
    def __init__(self, cluster_name, provider_config):
        self.cluster_name = cluster_name
        self.provider_config = provider_config
    
    def nodearrays(self):
        '''pprint.pprint(json.dumps(json.loads(dougs_example)))'''
        return self._add_missing_limits(self.get("/nodearrays?cluster=%s" % self.cluster_name))
    
    def _add_missing_limits(self, arrays):
        known_machine_limits = {"Standard_B2s": 6,
                                "Standard_B2ms": 10,
                                "Standard_B4ms": 0,
                                "Standard_D2_v2": 100,
                                "Standard_D3_v2": 100
                                }
        for a in arrays["nodeArrays"]:
            a["maxCoreCount"] = 100
            for b in a["buckets"]:
                b["maxCount"] = None
                b["maxCoreCount"] = known_machine_limits.get(b["overrides"]["MachineType"], 100)
        return arrays

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
        # kludge: work around
        fexpr = 'NodeId in {%s}' % ",".join(['"%s"' % x for x in node_ids])
        try:
            self.post("/cloud/actions/terminate_node/%s" % self.cluster_name, json={"filter": fexpr})
        except Exception as e:
            if "No nodes were found matching your query" in unicode(e):
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
    
    def post(self, url, data=None, json=None, **kwargs):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        session = self._session()
        response = session.post(root_url + url, data, json, **kwargs)
        if response.status_code != 200:
            raise ValueError(response.content)
        
    def get(self, url, **params):
        root_url = self._get_or_raise("cyclecloud.config.web_server")
        session = self._session()
        response = session.get(root_url + url, params=params)
        if response.status_code != 200:
            raise ValueError(response.content, object_pairs_hook=collections.OrderedDict)
        return json.loads(response.content)
