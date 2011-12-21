# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
The PluginManager loads plugins and offers simple methods to activate
and deactivate the plugins once they are loaded.
"""

import os
import sys
import cPickle
from log import log
from Queue import Queue
from pattern import singleton
from plugin_web  import WebPlugin
from plugin_thread import ThreadPlugin
from content import content
from pprint import pprint 

class PluginManager(object):
    """
    Manage several plugins by ordering them in categories.
    Search and load the plugins from target directory.
    """

    PLUGIN_DIRECTORY = '/var/lib/mediaplat/plugins'
    PLUGIN_SETTINGS  = os.path.join(PLUGIN_DIRECTORY, 'settings.p')

    def __init__(self):
        """
        Initialize the plugin_pool and set the module/db queue pool. 
        And scanning plguin path and load all plugins

        # plugin_pool = { 'online_meta' : { 'category' : 'FS', 'is_activated' : True, 'desc' : ... }, }
        # plugin_cls  = { 'online_meta' : : <__main__.Foo instance> }
        # mqueue_pool = { 'online_meta' : queue }
        """
        self.plugin_pool = dict()
        self.plugin_cls  = dict()
        self.mqueue_pool = dict()

        self.__load_config()
        sys.path.append(self.PLUGIN_DIRECTORY)

    def stop(self):
        """
        Exit the runtime context manager. 
        Should be used to the identifier in the as clause of with statements
        """
        try:
            for plugin in self.plugin_pool:
                if self.plugin_pool[plugin]['category'] in ['FS']:
                    self.plugin_cls[plugin].deactivate()

        except IOError:
            log.exception('PluginManager failed to terminated')
        else:
            log.info('PluginManager gracefully terminated')


    @classmethod
    def get_plugin_info(self):
        """
        Return plugin information dict for Web Interface.
        It include name, desc and activate info.

        @return : plugin information dictionary
        @rtype  : dict
        """
        modules = {}
        plugins = cPickle.load(open(self.PLUGIN_SETTINGS, 'rb'))
        for mod_name, mod_info in plugins.items():
            category = mod_info['category']
            if not modules.get(category):
                modules[category] = []
            modules[category].append((mod_name, mod_info['desc'], mod_info['is_activated']))
        return modules

    def push_queue(self, new_file):
        """
        Feed new file information to all module-queues for monitor thread.

        @param new_file: (inode, file_path) 
        @type  new_file: tuple
        """

        map(lambda queue: queue.put(new_file), self.mqueue_pool.values())

    def add(self, plugin_path):
        """
        Append a new plugin to the given category.

        @param plugin_path: local file path of current plugin 
        @type  plugin_path: str
        """
        base_plugin_modules = ['ThreadPlugin', 'WebPlugin']

        py_file = os.path.splitext(plugin_path)[0]
        modules = __import__(py_file)
        for mod in dir(modules):
            if mod.startswith('__') or mod in base_plugin_modules:
                continue
            cls = getattr(modules, mod)
            if type(cls) == type(object) and issubclass(cls, (WebPlugin, ThreadPlugin)):
                plugin = cls()
                try:
                    self.plugin_cls[plugin.name] = plugin

                    if not self.plugin_pool.get(plugin.name) or \
                       self.plugin_pool[plugin.name].get('is_activated'):
                        self.activate(plugin.name)

                except AttributeError:
                    log.exception("Unable to execute the code in plugin: %s" % plugin_path)
                    return "Invalid plugin type"
                else:
                    self.__store_config()

    def remove(self, plugin_name):
        """
        Remove a plugin from the category where it's assumed to belong.

        @param plugin_name: name of plugin which should be already added
        @type  plugin_name: str
        """
        plugin = self.plugin_cls.get(plugin_name)

        try:
            self.deactivate(plugin_name)
            del self.plugin_pool[plugin_name]
            del self.plugin_cls[plugin_name]
            plugin.cleanup()
        except IOError:
            log.exception("Unable to deactivate plugin: %s" % plugin_name)
            return "failed to remove plugin"
        else:
            self.__store_config()

    def activate(self, plugin_name):
        """
        Activate a plugin corresponding to a given name.
        Caller should decorate this method with try ~ except statement. 

        @param plugin_name: name of plugin which should be already added
        @type  plugin_name: str
        """
        instance = self.plugin_cls.get(plugin_name)

        if not instance.is_activated:
            # create module queue
            if isinstance(instance, ThreadPlugin):
                mod_queue = Queue()
                self.mqueue_pool[plugin_name] = mod_queue
                instance.set_queues(mod_queue)
                instance.set_push_back(content.add_data)

            instance.activate()
            self.plugin_pool[plugin_name] = {
                                'desc' : instance.desc,
                            'category' : instance.category,
                        'is_activated' : True, }
            self.__store_config()

    def deactivate(self, plugin_name):
        """
        Deactivate a plugin corresponding to a given name.

        @param plugin_name: name of plugin which should be already added
        @type  plugin_name: str
        """
        instance = self.plugin_cls.get(plugin_name)

        if instance.is_activated:
            # create module queue
            if isinstance(instance, ThreadPlugin) and instance.need_mqueue: 
                del self.mqueue_pool[plugin_name]

            instance.deactivate()
            self.plugin_pool[plugin_name]['is_activated'] = False
            self.__store_config()

    def __store_config(self):
        """
        Pickling current settings to files.
        """
        cPickle.dump(self.plugin_pool, open(self.PLUGIN_SETTINGS, 'wb'))

    def __load_config(self):
        """
        Unpickling from file to current settings.
        """
        try:
            self.plugin_pool = cPickle.load(open(self.PLUGIN_SETTINGS, 'rb'))
        except (KeyError, IOError):
            log.exception('PluginManager failed to load settings')

    def load_all_plugins(self):
        """
        Load the list of all plugins (belonging to all categories).
        """
        for file in os.listdir(self.PLUGIN_DIRECTORY):
            if file.endswith('.py') and not file.startswith('__'):
                self.add(file)

        log.info('PluginManager finished plugin loading')

plugin_manager = PluginManager()
