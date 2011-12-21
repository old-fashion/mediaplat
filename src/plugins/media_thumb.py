# -*- coding: utf-8 -*-

from os import path, devnull
from subprocess import call
from pymediainfo import MediaInfo
from plugin_thread import ThreadPlugin
from config import settings
from binascii import a2b_base64
from log import log

class MediaThumbPlugin(ThreadPlugin):
    name = 'media_thumb'
    desc = 'media thumbnail module'

    EXT_EPEG_SUPPORT = ('jpg', 'jpeg', 'jpe', 'jif', 'jfif', 'mpo', 'jps')

    def plugin_main(self, new_file):
        inode, file_path = new_file

        ext = path.splitext(file_path)[1][1:].lower()

        thumb_dir  = settings.get('thumbnail', 'path')
        thumb_file = path.join(thumb_dir, inode + '.jpg')

        # Extract base image
        if ext in self.EXT_VIDEO:
            fnull = open(devnull, 'w')
            command = ['ffmpeg', '-i', file_path, '-y', '-vframes', '1', '-ss', '00:00:01', '-an', thumb_file]
            call(command, shell = False, stdout = fnull, stderr = fnull)
            fnull.close()
        elif ext in self.EXT_AUDIO:
            media_info = MediaInfo.parse(file_path)
            if media_info.tracks[0].cover == 'Yes':
                cover_data = media_info.tracks[0].cover_data
                open(thumb_file,'wb').write(a2b_base64(cover_data))
            else:
                audio_dir = path.dirname(file_path)
                for folder_cover in ['Folder.jpg', 'folder.jpg', 'Cover.jpg', 'cover.jpg']:
                    audio_cover = path.join(audio_dir, folder_cover)
                    if path.exists(audio_cover):
                        command = ['convert', audio_cover, thumb_file]
                        call(command)
        else:
            if not ext in self.EXT_EPEG_SUPPORT:
                if ext == 'gif':
                    command = ['convert', file_path + "[0]", thumb_file]
                else:
                    command = ['convert', file_path, thumb_file]
                call(command)
            else:
                thumb_file = file_path
                
        # Generate thumbnail
        for size in settings.get('thumbnail', 'size').split(','):
            WxH = settings.get('thumbnail', size)
            filename = [ inode, size, 'jpg' ]
            command = ['epeg', '-m', WxH, thumb_file, path.join(thumb_dir, '.'.join(filename))]
            call(command)

        self.push_back({'uid' : inode, 'module' : self.name, 'has_thumbnail': 'true'})
        log.debug("{} module finished: {}".format(self.name, new_file[1]))
