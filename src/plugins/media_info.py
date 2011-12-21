# -*- coding: utf-8 -*-

from pymediainfo import MediaInfo
from plugin_thread import ThreadPlugin
from log import log

class MediaInfoPlugin(ThreadPlugin):
    name = 'media_info'
    desc = 'media info'

    def plugin_main(self, new_file):
        inode, file_path = new_file
        media_info = MediaInfo.parse(file_path)
        log.debug('Parsing %s' % file_path)

        meta = {}

        for track in media_info.tracks:
            try:
                if track.track_type == 'General':
                    ext = track.file_extension
                    meta['mime'] = self.get_mimetype(ext)
                    meta['container'] = track.format

                    if track.track_name:
                        meta['track_name'] = track.track_name
                    if track.album:
                        meta['album'] = track.album
                    if track.genre:
                        meta['genre'] = track.genre
                    if track.performer:
                        meta['artist'] = track.performer
                    if track.track_name_position:
                        meta['track_number'] = track.track_name_position

                elif track.track_type == 'Video':
                    meta['category'] = 'video'
                    meta['video_codec'] = track.format

                    if track.other_duration:
                        meta['duration'] = str(track.other_duration[-1])

                    if track.width:
                        meta['width']  = track.width
                    else:
                        log.error('width is None!')

                    if track.height:
                        meta['height'] = track.height
                    else:
                        log.error('height is None!')

                elif track.track_type == 'Audio':
                    if not meta.get('category'):
                        meta['category'] = 'audio'
                    meta['audio_codec'] = track.format
                    if track.other_duration:
                        meta['duration'] = str(track.other_duration[-1])

                elif track.track_type == 'Image':
                    meta['category'] = 'image'
                    if track.width:
                        meta['width']  = track.width
                    else:
                        log.error('width is None!')

                    if track.height:
                        meta['height'] = track.height
                    else:
                        log.error('height is None!')

                    if track.width and track.height:
                        meta['ratio'] = str(float(track.width) / float(track.height))
            except:
                log.exception('Fail to extract media info')

        if not meta.get('category'):
            meta['category'] = 'document'

        meta['uid']    = inode
        meta['module'] = self.name
        self.push_back(meta)
        log.debug("{} module finished: {}".format(self.name, new_file[1]))
