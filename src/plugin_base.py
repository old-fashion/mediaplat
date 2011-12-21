# -*- coding: utf-8 -*-

import os
from log import log

class InvalidPluginType(Exception):
    """ Plugin type is not suitable """ 

class MissingPluginInfo(Exception):
    """ Some Plugin information is not provided """ 

class MediaPlugin(object):
    """
    The simple interface to be inherited when creating a plugin.

    Representation of the basic set of information related to a
    given plugin such as its name, version, description...
    """

    name = None
    desc = None
    category = None
    
    def __init__(self):
        """
        Set the basic variables.

        The name of plugin should be unique through all categories.
        """
        if not self.name or not self.desc or not self.category:
            raise MissingPluginInfo

        self.is_activated = False 

        self.more_info = {
            'path' : os.path.abspath(__file__),
            'icon' : None,
            'version' : None,
        }

        self.activate_cb   = None
        self.deactivate_cb = None

    def activate(self):
        """
        Called at plugin activation.
        """
        self.is_activated = True
        if self.activate_cb:
            self.activate_cb()

        log.info('Plugin is activated : ' + self.name)

    def deactivate(self):
        """
        Called when the plugin is disabled.
        """
        self.is_activated = False
        if self.deactivate_cb:
            self.deactivate_cb()

        log.info('Plugin is deactivated : ' + self.name)

    def cleanup(self):
        """
        Remove all temporarily created files
        """
        os.remove(self.more_info['path'])
