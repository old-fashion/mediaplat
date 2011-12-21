from config import settings
from django.shortcuts import render_to_response
from django.template import RequestContext
from plugin_manager import PluginManager
from mediaplat import Mediaplat
from content import content
from log import log
from util import *
import re
from zipfile import ZipFile, BadZipfile
from django.core.files import File
from airplay.airplay import airplay

menu_list    = ['setting', 'search', 'image', 'audio', 'video', 'folder']
submenu_list = ['log', 'modules', 'configuration']

def robby(request, menu):
    next, args = Broker().do_action(request, menu)
    return render_to_response(next, args, context_instance=RequestContext(request))

class Broker(object):

    def __init__(self):
        self.args = { 'menu_list' : menu_list }

    def do_action(self, request, action):
        """
        Prepare page arguments and next page which forward to 

        @return : (next page, page arguments)
        @rtype  : tuple
        """

        """
        For calling the log.html about all log title
        by yongjae
        """
        if (bool(re.match('log', action))):
            action = 'log'

        return getattr(self, '_do_' + action, self._do_folder)(request)

    def _prepare_browse(self, request):
        self.args['start'] = str(request.GET.get('start', 0))
        self.args['count'] = str(request.GET.get('count', settings.get('web', 'count_per_page')))

        page = int(request.GET.get('page', '0'))
        if self.args['id'].find('image') < 0:
            request_count = int(settings.get('web', 'count_per_page'))
        else:
            request_count = int(settings.get('web', 'image_per_page'))
        start_index = request_count * page

        self.args['self'] = content.browse_metadata(self.args['id'])

        if self.args['self'].get('type') == 'container':
            self.args['single'] = False
            self.args['parents'] = content.parents(self.args['id'])
            self.args['rows'] = content.browse_children(self.args['id'], 
                                start_index = start_index, request_count = request_count)
            self.args['cur_page'] = page
            page_node = self.args['self']
        else:
            self.args['single'] = True
            self.args['parents'] = content.parents(self.args['self'].get('pid'))
            self.args['rows'] = [ self.args['self'] ]
            self.args['cur_page'] = page
            #page_node = content.browse_metadata(self.args['self'].get('pid'))
            page_node = self.args['self']

        self.args['page_range'] = range(page_node.get('child_count', 0) / request_count + 1) 
        items = page_node.get('child_item_count', 0)
        containers = page_node.get('child_container_count', 0)
        self.args['items'] = pretty_count([(containers, " container", " containers"), (items, " item", " items")])

    def _pretty_format(self, request, row):
        if 'debug' in request.GET:
            debug = "[{0}] ".format(row['uid'])
        else:
            debug = ""

        row['linkname'] = row['name']
        row['size'] = pretty_size(int(row.get('size', '0')))
        row['date'] = row.get('date', '')[:-3]
        if 'track_number' in row:
            row['track_number'] = '#' + row['track_number']
        if 'category' in row and row['category'] == 'audio':
            if 'track_name' in row and row['pid'].find('audio') > 0:
                row['name'] = row['track_name']

        if row['type'] == 'container':
            row['desc'] = debug + "{} items".format(row.get('child_count', '0'))
        else:
            row['desc'] = {
                'video': debug + "Video " + row.get('width', '0') + "x" + row.get('height', '0'),
                'audio': debug + "Audio " + row.get('track_number', '') + " " + row.get('duration', '.000')[:-4],
                'image': debug + "Image " + row.get('width', '0') + "x" + row.get('height', '0'),
                'document': debug + "Document",
            }.get(row.get('category', 'document'))

    def _pretty_search(self, request, row):
        keyword = request.GET.get('keyword').encode('utf8')
        regx = re.compile(r'({})'.format(keyword), re.IGNORECASE)
        row['name'] = regx.sub(r'<span id=searched>\1</span>', row['name'])

    def _do_folder(self, request):
        self.args['id'] = str(request.GET.get('id', content.FOLDER))
        self._prepare_browse(request)

        for row in self.args['rows']:
            self._pretty_format(request, row)

        self.args['cur_menu']   = 'folder'
        return ('folder.html', self.args)

    def _do_video(self, request):
        self.args['id'] = str(request.GET.get('id', content.VIDEO))
        self._prepare_browse(request)
        if self.args['self'].get('child_container_count', 0) != 0:
            for row in self.args['rows']:
                self._pretty_format(request, row)
        else:
            self.args['view_mode'] = 'on'
            for row in self.args['rows']:
                row['video_width'], row['video_height'] = \
                    get_resize(row.get('width', 0), row.get('height', 0), 900, 600)
                row['fullpath'] = content.fullpath(row['uid']).lstrip(settings.get("web", "path_base"))

        self.args['cur_menu'] = 'video'
        return ('video.html', self.args)

    def _do_audio(self, request):
        if request.method == 'POST':
            try:
                action = request.POST.get('action')

                if action == 'Start Play':
                    uid        = request.POST.get('uid')
                    device_idx = request.POST.get('device_idx')
                    host       = request.META.get('HTTP_HOST')
                    airplay.send_audio(host, uid, int(device_idx))
                elif action == 'Refresh Device' and \
                     settings.get('airplay', 'enable') == 'True':
                    airplay.discovery()
            except:
                log.exception('Fail to airplay send_audio')

        self.args['id'] = str(request.GET.get('id', content.AUDIO))
        self._prepare_browse(request)
        uid = self.args['id']
        if uid == 'audio_album' or uid == 'audio_artist':
            self.args['view_mode'] = 'on'
            for row in self.args['rows']:
                if uid == 'audio_album':
                    row['audiotitle'] = row.get('album', '')
                    row['audiodesc'] = row.get('artist', '')
                elif uid == 'audio_artist':
                    row['audiotitle'] = row.get('artist', '')
                    row['audiodesc'] = pretty_count([(row.get('child_count', '0'), " Song", " Songs")])
        else:
            for row in self.args['rows']:
                self._pretty_format(request, row)

        self.args['cur_menu'] = 'audio'
        return ('audio.html', self.args)

    def _do_image(self, request):
        if request.method == 'POST':
            try:
                action = request.POST.get('action')

                if action == 'Start Play':
                    uid        = request.POST.get('uid')
                    device_idx = request.POST.get('device_idx')
                    airplay.send_image(uid, int(device_idx))
                elif action == 'Refresh Device' and \
                     settings.get('airplay', 'enable') == 'True':
                    airplay.discovery()
            except:
                log.exception('Fail to airplay send_image')

        self.args['id'] = str(request.GET.get('id', content.IMAGE))
        self.args['devices'] = airplay.devices
        self._prepare_browse(request)
        if self.args['self'].get('child_container_count', 0) != 0:
            for row in self.args['rows']:
                self._pretty_format(request, row)
        else:
            self.args['view_mode'] = 'on'
            content.sort(self.args['rows'], 'ratio')
            for row in self.args['rows']:
                row['thumbnail_width'], row['thumbnail_height'] = \
                    get_resize(row.get('width', 0), row.get('height', 0), 180, 135)

        self.args['cur_menu'] = 'image'
        return ('image.html', self.args)

    def _do_search(self, request):
        self.args['id'] = str(request.GET.get('id', content.FOLDER))
        self.args['total_item'] = pretty_count([(content.total()[2], " item", " items")])
        self.args['cur_menu'] = 'search'
        keyword = request.GET.get('keyword', '').encode('utf8')

        if keyword.strip() == '' :
            pass
        else:
            self.args['searched'] = True
            result = content.search_keyword(keyword, self.args['id'])
            for category in result:
                for row in result[category]:
                    self._pretty_format(request, row)
                    self._pretty_search(request, row)

            if len(result) == 0:
                result['not found'] = []

            self.args['categories'] = result

        return ('search.html', self.args)

    def _do_setting(self, request):
        return self._do_configuration(request)
 
    def _do_configuration(self, request):
        if request.method == 'POST':
            try:
                section = request.POST.get('section')
                option  = request.POST.get('option')
                value   = request.POST.get(option)

                Mediaplat.request({'module' : 'settings', 
                                   'action' : 'set_value', 
                                   'params' : (section, option, value)})

                settings.load_settings()
            except:
                log.exception('Fail to apply configuration changes')

        self.args['cur_menu']     = 'setting'
        self.args['submenu']      = 'configuration'
        self.args['submenu_list'] = submenu_list
        self.args['settings']     = settings.to_data()
        return ('configuration.html', self.args)

    def _do_modules(self, request):
        if request.method == 'POST':
            try:
                if 'file' in request.FILES:
                    file = request.FILES['file']

                    fname = file.name.encode('utf-8')
                    tmp_upload_path = '/tmp/{}'.format(fname)
                    fp = open(tmp_upload_path, 'wb')
                    for chunk in file.chunks():
                        fp.write(chunk)
                    fp.close()

                    zip = ZipFile(tmp_upload_path, 'r')
                    zip.extractall(path=PluginManager.PLUGIN_DIRECTORY)

                    Mediaplat.request({'module' : 'plugin_manager', 
                                       'action' : 'load_all_plugins', 
                                       'params' : None})
                else:
                    action = request.POST.get('action')
                    plugin = request.POST.get('plugin')

                    if action not in ['activate', 'deactivate', 'remove']:
                        log.error('Invalid request : ' + action)
                    else:
                        Mediaplat.request({'module' : 'plugin_manager', 
                                           'action' : action, 
                                           'params' : (plugin)})
            except (IOError, BadZipfile):
                log.exception('module error')
        
        self.args['cur_menu']     = 'setting'
        self.args['submenu']      = 'modules'
        self.args['submenu_list'] = submenu_list
        self.args['modules']      = PluginManager.get_plugin_info()
        return ('modules.html', self.args)
        
    def _do_log(self, request):
        self.args['cur_menu']     = 'setting'
        self.args['submenu']      = 'log'
        self.args['log']          = []
        self.args['log_files']    = ['mediaplat', 'server', 'db', 'web']
        self.args['submenu_list'] = submenu_list

        COLOR_MAP = {'DEBUG'   : 'BLUE', 'INFO'  : 'BLACK', 'CRITICAL'  : 'YELLOW', 
                     'WARNING' : 'GRAY', 'ERROR' : 'RED',  'EXCEPTION' : 'RED'}

        try:
            log_file = re.search('log_(\w+)', request.path).group(1)
        except AttributeError:
            log_file = 'mediaplat'

        try:
            self.args['log'] = open('{}/{}.log'.format('/var/log/mediaplat', 
                                     log_file)).readlines()[:-100:-1]
        except IOError:
            log.error('Log file is not exists : ' + log_file)

        self.args['target_log'] = log_file
        self.args['color_tag']  = COLOR_MAP
        return('log.html', self.args)
