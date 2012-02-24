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

def import_setting(name, default=None):
    param = getattr(settings, name, default)
    if isinstance(param, basestring) and '.' in param:
        param = import_path(param, default)
    return param

# import module by import_path
def import_path(import_path, alternate=None):
    from django.utils.importlib import import_module
    try:
        module_name, value_name = import_path.rsplit('.', 1)
        module = import_module(module_name)
        value_name = getattr(module, value_name)
    except ImportError:
        value_name = alternate
    except AttributeError:
        value_name = alternate
    return value_name