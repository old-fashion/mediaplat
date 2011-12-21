# -*- coding: utf-8 -*-

import time
import select
import pybonjour
from os import path, system
from config import settings
from content import content
from bonjour import Bonjour
import urllib2
from keepalive import HTTPHandler

class Airplay(Bonjour):

    header = {'Content-Type'       : 'application/x-www-form-urlencoded',
              'Connection'         : 'keep-alive',
              'User-Agent'         : 'MediaControl/1.0',
              'X-Apple-Transition' : 'Dissolve',
              'Keep-Alive'         : '30'}


    def __init__(self):
        super(Airplay, self).__init__()
        self.opener = urllib2.build_opener(HTTPHandler())
        urllib2.install_opener(self.opener)

    def discovery(self, regtype = '_airplay._tcp'):
        return super(Airplay, self).discovery(regtype)

    def send_audio(self, host, uid, device_idx):
        data = 'Content-Location: http://{}/file/id/{}\nStart-Position: 0\n'.format(host, uid)
        self.header['Content-Length'] = len(data)           
        request = urllib2.Request('http://192.168.1.5:7000/play', data=data, headers=self.header)
        request.get_method = lambda: 'POST'
        url = opener.open(request)

    def send_image(self, uid, device_idx):
        meta   = content.browse_metadata(str(uid))

        if meta is not None:
            if meta.get('type') == 'container':
                for item in content.browse_children(str(uid)):
                    self._display_single(item['uid'], device_idx)
            else:
                self._display_single(uid, device_idx)

    def _display_single(self, uid, device_idx):
        full_path = content.fullpath(uid)
        unit_time = settings.get('airplay', 'time_per_slide')

        if full_path is not None:
            data   = open(full_path).read()
            self.header['Content-Length'] = len(data)           
            request = urllib2.Request('http://{}:7000/photo'.format(self.devices[device_idx]), data=data, headers=self.header)
            request.get_method = lambda: 'PUT'
            url = self.opener.open(request)
            time.sleep(int(unit_time))
            

airplay = Airplay()

if settings.get('airplay', 'enable') == 'True':
    airplay.discovery()
