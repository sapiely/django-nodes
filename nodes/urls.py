from django.conf.urls.defaults import *
from models import NodeMain

urlpatterns = patterns('',
    # node main url entry
    url(r'^'
         r'(?P<path>[a-zA-Z0-9-_/]+?)/'
          r'(i/(?P<item>[a-zA-Z0-9-_]+)(/|$))?'
           r'$', 'nodes.views.main', {'node_name':'main'}, name='nodes_main'),
)