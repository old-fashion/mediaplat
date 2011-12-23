from django.conf.urls.defaults import * 
from glob import glob
from os import path

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

conffiles = glob(path.join(path.dirname(__file__), 'conf', '*.conf'))
conffiles.sort()
for f in conffiles:
    url_base = path.splitext(path.basename(f))[0]
    urlpatterns += patterns('', url(r'^{}/'.format(url_base), include('{}.urls'.format(url_base))))
