import unittest
from plugin_thread import ThreadPlugin

class TestClass(ThreadPlugin):
    name = 'test_thread_plugin'

class TestThreadPlugin(unittest.TestCase):
    def test___init__(self):
        try:
            cls = TestClass()
        except:
            assert False
        else:
            assert True

    def test_activate(self):
        cls = TestClass()
        cls.activate()
        assert cls.is_activated == True
        
    def test_deactivate(self):
        cls = TestClass()
        cls.deactivate()
        assert cls.is_activated == False

if __name__ == '__main__':
    unittest.main()
