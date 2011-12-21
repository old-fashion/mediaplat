# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
The ConfigManager maintain system-wide default settings. 
And controls request from/to configuration file.

methods
 - get(section, option)
   : Get an option value for the named section.
 - set(section, option, value)
   : If the given section exists, set the given option to the specified value; otherwise raise NoSectionError
 - flush()
   : Write back in memory settings to file.
"""

from log import log
from os import stat, path, mkdir
from pattern import singleton
from ConfigParser import ConfigParser

@singleton
class Config(ConfigParser):
    
    CONF_FILE_PATH = '/etc/mediaplat/mediaplat.conf'

    def __init__(self):
        """
        Initialize the configuration dictionary and load settings from file.
        """
        ConfigParser.__init__(self)

        if not path.exists(self.CONF_FILE_PATH):
            open(self.CONF_FILE_PATH, 'w')

        self.load_settings()

    def load_settings(self):
        """
        Load settings from file system and remeber it's last modified time
        """
        try:
            self.read(self.CONF_FILE_PATH)
            self.check_path_exists()
        except:
            log.exception('Fail to read configuration files')


    def check_path_exists(self):
        """
        Iterate settings and create non-exists path
        """
        for section in self.sections():
            for option, value in self.items(section):
                if option in ['path'] and not path.exists(value):
                    try:
                        mkdir(value)
                        log.info('New folder is created : {}'.format(value))
                    except:
                        log.exception('Fail to create folder : {}'.format(value))


    def to_data(self):
        """
        Return all settings as dict

        @return : options and values including all sections 
        @rtype  : dict
        """
        comments = {'core'      : {'base'         : 'default monitoring path',
                                   'aggregation'  : 'use data aggregation (True / False)',
                                   'deny_keyword' : 'do not allow to display keywords'},
                    'search'    : {'max_result' : 'upper limit of search items'},
                    'web'       : {'count_per_page' : 'max number of items in one page',
                                   'image_per_page' : 'max number of images in one page'},
                    'airplay'   : {'enable'         : 'use airplay capability (True/ False)',
                                   'time_per_slide' : 'time interval between images' },
                    'thumbnail' : {'path'   : 'thumbnail default path',
                                   'size'   : 'list of thumbnail types',
                                   'large'  : 'size of large thumbnail',
                                   'medium' : 'size of medium thumbnail',
                                   'small'  : 'size of small thumbnail'},
                    'transcode' : {'iPhone'   : 'transcoded file path for iPhone',
                                   'iPad'     : 'transcoded file path for iPad'}}
        res = {}
        for line in open(self.CONF_FILE_PATH):
            line = line.strip()
            if not line:    
                continue
            if line.startswith('['):
                section = line[1:-1]
                res[section] = []
            else:
                option, value = map(lambda str:str.strip(), line.split('='))
                res[section].append((option, value, comments[section].get(option, '')))
        return res


    def set_value(self, section, option, value):
        """
        Set configurations. (wrapping method only for web ui)
        """
        self.set(section, option, value)
        self.flush()
        log.info('Configuration set request, [{}], {} : {}'.format(section, option, value))


    def flush(self):
        """
        Write back current settings to file.
        Thie method should be called before mediaplat terminated.
        """
        try:
            self.write(open(self.CONF_FILE_PATH, 'w'))
        except:
            log.exception('Fail to write configuration files')

settings = Config()
