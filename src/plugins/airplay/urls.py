from django.conf.urls.defaults import *
from views import image_serve, device_discovery

urlpatterns = patterns('',
    (r'^discovery/$', device_discovery),
    (r'^image/(?P<uid>[^/]+)/(?P<device_idx>\d+)$', image_serve),
)
