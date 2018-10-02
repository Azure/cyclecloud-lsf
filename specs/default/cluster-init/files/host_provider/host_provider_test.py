import unittest
from host_provider import CycleCloudProvider


class MockCluster:
    def __init__(self, nodearrays):
        self._nodearrays = nodearrays
        
    def nodearrays(self):
        return self._nodearrays
    
    def add_node(self, request):


class Test(unittest.TestCase):


    def test_host_prov(self):
        cluster = MockCluster([{"Name": "execute", "MachineType": [{"Name": "A4", "CoreCount": 4, "Memory": 1024, "Location": "ukwest"}]}])
        json_writer = lambda x: x
        provider = CycleCloudProvider(cluster, json_writer)
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(1, len(templates))
        self.assertEquals("execute@A4", templates[0]["templateId"])
        self.assertEquals(["Numeric", 4], templates[0]["attributes"]["ncores"])
        self.assertEquals(["Numeric", 2], templates[0]["attributes"]["ncpus"])
        
        cluster._nodearrays.append({"Name": "execute", "MachineType": [{"Name": "A8", "CoreCount": 8, "Memory": 2048, "Location": "ukwest"}]})
        
        templates = provider.templates()["templates"]
        
        self.assertEquals(2, len(templates))
        a4 = [t for t in templates if t["templateId"] == "execute@A4"][0]
        a8 = [t for t in templates if t["templateId"] == "execute@A8"][0]
        
        self.assertEquals(["String", "ukwest"], a4["attributes"]["zone"])
        self.assertEquals(["Numeric", 4], a4["attributes"]["ncores"])
        self.assertEquals(["Numeric", 2], a4["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 1024], a4["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a4["attributes"]["type"])
        
        self.assertEquals(["String", "ukwest"], a8["attributes"]["zone"])
        self.assertEquals(["Numeric", 8], a8["attributes"]["ncores"])
        self.assertEquals(["Numeric", 4], a8["attributes"]["ncpus"])
        self.assertEquals(["Numeric", 2048], a8["attributes"]["mem"])
        self.assertEquals(["String", "X86_64"], a8["attributes"]["type"])
        
        request = provider.request( {"user_data": {},
                                       "rc_account": "default",
                                       "template":
                                        {
                                            "templateId": "execute@A4",
                                            "machineCount": 1
                                        }
                                    })


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.test_host_prov']
    unittest.main()