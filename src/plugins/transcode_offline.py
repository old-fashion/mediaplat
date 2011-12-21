# -*- coding: utf-8 -*-

from os import path, devnull
from subprocess import call
from pymediainfo import MediaInfo
from plugin_thread import ThreadPlugin
from config import settings
from binascii import a2b_base64
from log import log

class TranscodeOfflinePlugin(ThreadPlugin):
    name = 'transcode_offline'
    desc = 'transcode_offline module'

    EXT_TRANS_AUDIO_SUPPORT = ('wav', 'aac')
    EXT_TRANS_VIDEO_SUPPORT = ('avi')

    def plugin_main(self, new_file):
        inode, file_path = new_file

        if bool('[iPhone]' in file_path) or bool('[iPad]' in file_path):
            return

        ext = path.splitext(file_path)[1][1:]
        filename = path.splitext(file_path)[0][:]

        #log.debug("filename:%s" % filename)
        #log.debug("ext:%s" % ext)
        #log.debug("file_path:%s" % file_path)

        """
        Convert file name
        """
        if '/iPhone' in file_path:
            trans_dir = settings.get('transcode','iPhone')
            #log.debug("trans_dir:%s" % trans_dir)

            filename  = filename[len(trans_dir)+1:]
            if ext in self.EXT_AUDIO:
                trans_aud_file = path.join(trans_dir, '[iPhone]'+ filename +'.mp3')
            elif ext in self.EXT_VIDEO:
                trans_vid_file = path.join(trans_dir, '[iPhone]'+ filename +'.mp4')
            else:
                return

        elif '/iPad' in file_path:
            trans_dir = settings.get('transcode','iPad')
            #log.debug("trans_dir:%s" % trans_dir)

            filename  = filename[len(trans_dir)+1:]
            if ext in self.EXT_AUDIO:
                trans_aud_file = path.join(trans_dir, '[iPad]'+ filename +'.mp3')
            elif ext in self.EXT_VIDEO:
                trans_vid_file = path.join(trans_dir, '[iPad]'+ filename +'.mp4')
            else:
                return

        else:
            #log.info("No transcoding for the wrong path.")
            return
        #log.debug("trans filename:%s" % filename)
        #log.debug("trans_aud_file:%s" % trans_aud_file)
        """
        Transcoding Audio or Video by ffmpeg
        """
        # Execute audio transcoding
        if ext in self.EXT_AUDIO:
            fnull = open(devnull, 'w')
            log.info("Audio Transcoding Start")
            command = ['ffmpeg', '-i', file_path, '-acodec', 'libmp3lame', '-ar', '48000', '-ab', '128k', '-ac', '2', trans_aud_file]

            call(command, shell = False, stdout = fnull, stderr = fnull)
            fnull.close()
            log.info("Audio Transcoding End")
        # Execute video transcdoing
        elif ext in self.EXT_VIDEO:
            return
        else:
            return

        self.push_back({'uid' : inode, 'module' : self.name})
