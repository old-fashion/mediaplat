from os import path
from plugin_web import WebPlugin

class AirplayPlugin(WebPlugin):
    
    name = 'airplay'
    desc = 'playback local files to apple devices'
    app_path = path.join(path.dirname(__file__), name)

    def __init__(self):
        super(AirplayPlugin, self).__init__()
        self.has_template = False
