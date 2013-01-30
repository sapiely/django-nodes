from django.conf.urls import patterns, url

urlpatterns = patterns('',
    # node main url entry
    url(r'^'
         r'(?P<path>[a-zA-Z0-9-_/]+?)/'
          r'(i/(?P<item>[a-zA-Z0-9-_]+)(/|$))?'
           r'$', 'content.views.main_view', {'node_name':'main'}, name='nodes_main'),
)