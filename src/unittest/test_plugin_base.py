import unittest
from plugin_base import MediaPlugin, MissingPluginInfo

class TestMediaPlugin(unittest.TestCase):
    def test___init__(self):
        try:
            plugin = MediaPlugin()
        except MissingPluginInfo: 
            assert True
        else:
            assert False 

if __name__ == '__main__':
    unittest.main()
