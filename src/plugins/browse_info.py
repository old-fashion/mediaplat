from os import path
from plugin_web import WebPlugin

class BrowsePlugin(WebPlugin):
    
    name = 'browse'
    desc = 'default browse, search and setting plugin tools'
    app_path = path.join(path.dirname(__file__), name)

    def __init__(self):
        super(BrowsePlugin, self).__init__()
        self.has_template = True
