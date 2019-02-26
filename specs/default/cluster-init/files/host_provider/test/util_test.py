import unittest

import util


class UtilTest(unittest.TestCase):

    def test_provider_config(self):
        self.assertEquals("d", util.ProviderConfig({"a": {"b": {"c": "d"}}}, {}).get("a.b.c"))
        self.assertEquals({"c": "d"}, util.ProviderConfig({"a": {"b": {"c": "d"}}}, {}).get("a.b"))
        
        # missing from user config, look in jetpack
        self.assertEquals("y", util.ProviderConfig({"a": {"b": {"c": "d"}}}, {"x": "y"}).get("x"))
        # fall back on default_value, if all else fails
        self.assertEquals("0", util.ProviderConfig({}, {"x": "y"}).get("z.a.b", "0"))
        # user config overrides jetpack
        self.assertEquals("d", util.ProviderConfig({"a": {"b": {"c": "d"}}}, {"a": {"b": {"c": "e"}}}).get("a.b.c"))
        
        pc = util.ProviderConfig({}, {})
        pc.set("a", "b")
        self.assertEquals("b", pc.get("a"))
        
        pc.set("x.y.z", "123")
        self.assertEquals("123", pc.get("x.y.z"))
        self.assertEquals({"z": "123"}, pc.get("x.y")) 
        self.assertEquals({"y": {"z": "123"}}, pc.get("x"))
        self.assertEquals({"x": {"y": {"z": "123"}}, "a": "b"}, pc.get(""))
        self.assertEquals({"x": {"y": {"z": "123"}}, "a": "b"}, pc.get(None))
        

if __name__ == "__main__":
    unittest.main()
