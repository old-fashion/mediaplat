from django.conf.urls.defaults import *
from file.views import *

urlpatterns = patterns('',
    (r'^id/(?P<uid>[^/]+)/.*$', forward_to_local),
    (r'^thumbnail/(?P<uid>[^/]+)/(?P<size>\w+)$$', thumbnail_serve),
)
