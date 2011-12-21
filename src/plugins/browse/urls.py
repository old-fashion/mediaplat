from django.conf.urls.defaults import *
from django.views import *
from browse.views import *
from os import path

urlpatterns = patterns('',
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': path.join(path.dirname(__file__), 'site_media')}),
    (r'^(?P<menu>.*)$', robby),
)
