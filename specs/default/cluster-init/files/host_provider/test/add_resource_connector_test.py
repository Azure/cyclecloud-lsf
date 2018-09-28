import unittest
import add_resource_connector


class AddresourceConnectorTest(unittest.TestCase):

    def test_schmod_demand(self):
        
        def run_test(raw, expected):
            input_lines = raw.splitlines(True)
            actual = add_resource_connector.enable_schmod_demand(input_lines)
            self.assertEquals(expected, actual)
            for n in range(len(expected)):
                self.assertEquals(expected[n], actual[n])
            
        run_test('''#schmod_demand\n''', ["#schmod_demand\n"])
        run_test(
'''#schmod_demand
bEgin pluginmOdule
#schmod_demand () ()    
# something schmod_demand
#      schmod_demand
eNd pluginModule
#schmod_demand
''', ["#schmod_demand\n",  # IGNORE: outside of pluginmodule
"bEgin pluginmOdule\n",
"schmod_demand () ()\n",  # UNCOMMENT: inside of pluginmodule
"# something schmod_demand\n",  # IGNORE: something before schmod_demand
"schmod_demand\n",  # UNCOMMENT: inside of pluginmodule
"eNd pluginModule\n",
"#schmod_demand\n"])  # IGNORE: outside of pluginmodule


if __name__ == "__main__":
    unittest.main()