# -*- coding: utf-8 -*-

import os
import shutil
from plugin_base import MediaPlugin

class WebPlugin(MediaPlugin):
    """
    The plugin interface to be inherited when creating a web plugin.
    WebPlugin is a kind of python-django app wrapper. It should have 
    following capabilites of 
        - modify or generate related settings
        - reload WSGI if requires 
    """
    category = 'WEB'
    app_path = None

    def __init__(self):
        """
        Set the basic web plugin variables.
        """
        super(WebPlugin, self).__init__()

        self.settings = ''
        self.has_template  = False
        self._django_setting_path = '/var/lib/mediaplat/www/conf'
        self._django_manage_path  = '/var/lib/mediaplat/www/manage.py'
        self._touch_reload_path   = '/tmp/reload'
        self.activate_cb   = self._install_app
        self.deactivate_cb = self._uninstall_app

    def _install_app(self):
        """
        Apply 3rd party plugin apps to django configuration files. 
            - urls.py
            - settings.py
        """
        INSTALLED_APPS = "INSTALLED_APPS += ('{}',)\n"
        TEMPLATE_DIRS  = "TEMPLATE_DIRS  += ('{}/templates',)\n"

        conf = open('{}/{}.conf'.format(self._django_setting_path, self.name), 'w')
        conf.write(self.settings)
        conf.write(INSTALLED_APPS.format(self.name))
        if self.has_template:
            conf.write(TEMPLATE_DIRS.format(self.app_path))
        conf.close()    
        self.reload_WSGI()

    def _uninstall_app(self):
        """
        Remove 3rd party plugin apps from django configuration files. 
            - urls.py
            - settings.py
        """
        conf = '{}/{}.conf'.format(self._django_setting_path, self.name)
        if os.path.exists(conf):
            os.remove(conf)
            self.reload_WSGI()

    def reload_WSGI(self):
        """
        Reload WSGI daemon to apply changes.
        """
        os.system('echo "no" | python {} syncdb > /dev/null'.format(self._django_manage_path))
        os.system('touch {}'.format(self._touch_reload_path))

    def cleanup(self):
        """
        Remove django app files.
        """
        super(WebPlugin, self).cleanup()
        if os.path.exits(self.app_path):
            shutil.rmtree(self.app_path)
