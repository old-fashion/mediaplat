from os import path
from plugin_web import WebPlugin

class FilePlugin(WebPlugin):
    
    name = 'file'
    desc = 'share local files to public'
    app_path = path.join(path.dirname(__file__), name)

    def __init__(self):
        super(FilePlugin, self).__init__()
        self.has_template = False
