from django.conf import settings

# exception
class NamespaceAllreadyRegistered(Exception):
    pass

# prepare request
def meta_to_request(request):
    if not hasattr(request, 'meta'):
        class MetaInRequest(object): pass
        request.meta                = MetaInRequest()
        request.meta.current        = None
        request.meta.chain          = []
        request.meta.title          = []
        request.meta.keywords       = []
        request.meta.description    = []

def cache_key_tool(lang, site_id, request, key=None):
    """Returns the language and site ID a cache key is related to if key=value, else generate key."""
    if key:
        return key.split('_', 3)[1:3]
    cache_name = getattr(settings, 'MENUS_CACHE_NAME', None)
    cache_name = 'menus_%s_%s_%s' % (lang, site_id, cache_name(request) if callable(cache_name) else 'key')
    return cache_name