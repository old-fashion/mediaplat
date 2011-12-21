# -*- coding: utf-8 -*-

import thread
from os.path import splitext
from plugin_base import MediaPlugin
from log import log

class ThreadPlugin(MediaPlugin):
    """
    The plugin interface to be inherited when creating a file-system
    related plugin. Each instance of ThreadPlugin runs as thread.
    And all thread shares mqueues(feed from monitor) and push_back method(feed to database).
    """
    category = 'FS'

    """
    Extension categorization table
    """
    EXT_VIDEO = ('asf', 'avc', 'avi', 'dv', 'divx', 'wmv', 'mjpg', 'mjpeg', 'mpeg', 'mpg', 'mpe', 'm2ts', 'mts', 'm2t', 
                 'tod', 'mod', 'mp2p', 'vob', 'mp2t', 'm1v', 'm2v', 'mpg2', 'mpeg2', 'vro', 'm4v', 'm4p', 'mp4ps', 'ts',
                 'ps', 'tp', 'ogm', 'mkv', 'rmvb', 'mov', 'hdmov', 'qt', 'bin', 'iso', 'swf', 'flv', 'm3u8', 'mp4')
    EXT_AUDIO = ('3gp', 'aac', 'ac3', 'aif', 'aiff', 'at3p', 'au', 'snd', 'dts', 'rmi', 'mid', 'mp1', 'mp2', 'mp3', 'm4a', 
                 'ogg', 'wav', 'pcm', 'lpcm', 'l16', 'wma', 'mka', 'ra', 'rm', 'ram', 'rv', 'flac')
    EXT_IMAGE = ('bmp', 'ico', 'emf', 'gif', 'jpeg', 'jpg', 'jpe', 'mpo', 'pcd', 'png', 'pnm', 'ppm', 'qti', 'qtf', 'qtif', 'dib')

    EXT_ALL = None
    EXT_MULTIMEDIA = EXT_VIDEO + EXT_AUDIO + EXT_IMAGE
    
    def __init__(self):
        """
        Set the basic file plugin variables.
        """
        super(ThreadPlugin, self).__init__()

        self.push_back = None
        self.activate_cb = self.start
        self.extension_list = self.EXT_MULTIMEDIA

    def set_push_back(self, fn):
        """
        Set the function to store key, value dictionary at database

        @param fn: function feed to backend database
        @type  fn: method
        """
        self.push_back = fn

    def set_queues(self, mqueue):
        """
        Set the module queue 

        @param mqueue: module queue feed from monitor/scanner
        @type  mqueue: instance of Queue
        """
        self.mqueue = mqueue

    def rebuild(self):
        """
        Remove all documents made before, and generate again
        """
        pass

    def plugin_main(self, new_file):
        """
        Thread main worker method. Inherited plugin should override this.

        @param new_file: (inode, file_path)
        @type  new_file: tuple
        """
        pass

    def run(self):
        """
        Start plugin's activity.
        """
        while self.is_activated:
            inode, file_path = self.mqueue.get()
            if self.extension_list:
                ext = splitext(file_path)[1][1:]
                if not ext.lower() in self.extension_list:
                    continue
            self.plugin_main((inode, file_path))

    def start(self):
        """
        Thread wrapper function.
        """
        thread.start_new_thread(self.run, ())

    def get_mimetype(self, ext):
        """
        Extension to mimetype mapping function

        @param ext: file extension
        @type  ext: str
        @return : mime type
        @rtype  : str
        """
        return {  #Video files
               'asf': 'video/x-ms-asf', 'avc': 'video/avi', 'avi': 'video/x-msvideo',
               'dv': 'video/x-dv', 'divx': 'video/avi', 'wmv': 'video/x-ms-wmv',
               'mjpg': 'video/x-motion-jpeg', 'mjpeg': 'video/x-motion-jpeg', 'mpeg': 'video/mpeg',
               'mpg': 'video/mpeg', 'mpe': 'video/mpeg', 'm2ts': 'video/mpeg', 'mts': 'video/mpeg',  
               'm2t': 'video/mpeg', 'tod': 'video/mpeg', 'mod': 'video/mpeg',  'mp2p': 'video/mp2p',
               'vob': 'video/mp2p', 'mp2t': 'video/mp2t', 'm1v': 'video/mpeg', 'm2v': 'video/mpeg2',
               'mpg2': 'video/mpeg2', 'mpeg2': 'video/mpeg2', 'vro': 'video/mpeg2',  'm4v': 'video/mp4',
               'm4p': 'video/mp4', 'mp4ps': 'video/x-nerodigital-ps', 'ts': 'video/mpeg',
               'ps': 'video/mpeg', 'tp': 'video/mpeg', 'trp': 'video/mpeg', 'dat': 'video/mpeg',
               'ogm': 'video/mpeg', 'mkv': 'video/mpeg', 'rmvb': 'video/mpeg', 'mov': 'video/mp4',
               'hdmov': 'video/quicktime', 'qt': 'video/quicktime', 'bin': 'video/mpeg', 'iso': 'video/mpeg',
               'mp4': 'video/mp4', 'swf': 'video/swf', 'flv': 'video/flv', 'k3g': 'video/kr3g',
               'm3u8': 'application/x-mpegURL',
               #Audio files 
               '3gp': 'audio/3gpp', 'aac': 'audio/x-aac', 'ac3': 'audio/x-ac3', 'aif': 'audio/aiff',
               'aiff': 'audio/aiff', 'at3p': 'audio/x-atrac3', 'au': 'audio/basic', 'snd': 'audio/basic',
               'dts': 'audio/x-dts', 'rmi': 'audio/midi', 'mid': 'audio/midi', 'mp1': 'audio/mpeg',
               'mp2': 'audio/mpeg', 'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'm4b': 'audio/mp4',
               'ogg': 'audio/x-ogg', 'wav': 'audio/wav', 'pcm': 'audio/L16', 'lpcm': 'audio/L16',
               'l16': 'audio/L16', 'wma': 'audio/x-ms-wma', 'mka': 'audio/mpeg', 'ra': 'audio/x-pn-realaudio',
               'rm': 'audio/x-pn-realaudio', 'ram': 'audio/x-pn-realaudio', 'rv': 'audio/x-pn-realaudio',  
               'flac': 'audio/x-flac', 'adt': 'audio/vnd.dlna.adts', 'adts': 'audio/vnd.dlna.adts', 
               #Images files 
               'bmp': 'image/bmp', 'dib': 'image/bmp', 'ico': 'image/x-icon', 'emf': 'image/x-emf',
               'gif': 'image/gif', 'jpeg': 'image/jpeg', 'jpg': 'image/jpeg', 'jpe': 'image/jpeg',
               'jps': 'image/x-jps', 'jif': 'image/jpeg', 'jfif': 'image/jpeg', 'mpo': 'image/mpo',
               'pcd': 'image/x-ms-bmp', 'png': 'image/png', 'pnm': 'image/x-portable-anymap',
               'ppm': 'image/x-portable-pixmap', 'qti': 'image/x-quicktime', 'qtf': 'image/x-quicktime',
               'qtif': 'image/x-quicktime', 'tif': 'image/tiff', 'tiff': 'image/tiff',
               'tga': 'image/tga', 'pcx': 'image/pcx', 'pgm': 'image/x-pgm', 'pbm': 'image/x-pbm',
            }.get(ext, '')
