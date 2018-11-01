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


if __name__ == "__main__":
    unittest.main()
