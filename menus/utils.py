from django.conf import settings

def meta_to_request(request):
    """prepare request for menus processing"""
    if not hasattr(request, 'meta'):
        class MetaInRequest(object): pass
        request.meta                = MetaInRequest()
        request.meta.current        = None
        request.meta.chain          = []
        request.meta.title          = []
        request.meta.keywords       = []
        request.meta.description    = []

def cache_key_generator(lang, site_id, request, key=None):
    """
    returns (language, site ID and cache key) values menu is related to
    if key is not None, else generate string key from received values
    """
    if key:
        return key.split('_', 3)[1:3]
    cache_name = getattr(settings, 'MENUS_CACHE_NAME', None)
    cache_name = cache_name(request) if callable(cache_name) else 'key'
    return 'menus_%s_%s_%s' % (lang, site_id, cache_name)

def setting_importable(name, default=None):
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