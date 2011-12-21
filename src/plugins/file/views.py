from os import path
from log import log
from config import settings
from content import content
from django.views import static
from django.http import Http404

def forward_to_local(request, uid):
    full_path = content.fullpath(uid)

    if full_path is None:
        log.error('requested uid({}) is invalid'.format(uid))
        raise Http404
    return static.serve(request, path=full_path, document_root='/')

def thumbnail_serve(request, uid, size):
    uid = content.original_uid(uid)
    if uid[0] == 'v':
        uid = uid[1:]
    thumb_dir = settings.get('thumbnail', 'path')
    full_path = path.join(thumb_dir, '{}.{}.jpg'.format(uid, size))

    if full_path is None:
        log.error('requested uid({}) or size({})is invalid'.format(uid, size))
        raise Http404
    return static.serve(request, path=full_path, document_root='/')
