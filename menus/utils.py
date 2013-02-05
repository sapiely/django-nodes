from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

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

def import_path(import_path, alternate=None):
    """import module by import_path"""
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

def check_menus_settings():
    """check menus settings validity"""

    # get menu settings for check
    from . import settings as msettings
    MENU_CONF = msettings.MENU_CONF
    DEFAULT_SCHEME = msettings.DEFAULT_SCHEME

    # todo: may be someway disable menus if improperly configured
    if not isinstance(MENU_CONF, dict) or not MENU_CONF.has_key('default'):
        raise ImproperlyConfigured('Menus "MENU_CONF" setting value is empty/incorrect'
                                   ' or not contains "default" key.')

    validvalue = lambda value, check: set(value).__len__() == value.__len__() \
                                      and all([v in check for v in value])
    errors = {}

    from . import registry
    for name, value in MENU_CONF.items():

        # check menus value
        menus = value.get('MENUS', None)
        if not menus or not validvalue(menus, registry.menus.keys()):
            errors[name] = 'Menus "%s" MENUS value (%s) is invalid.' % (name, menus)
            continue

        # check modifiers value
        modifiers = value.get('MODIFIERS', None)
        if not isinstance(modifiers, (list, tuple,)):
            modifkeys = registry.modifiers.keys()
            modifiers = [m for m in DEFAULT_SCHEME['MODIFIERS'] if m in modifkeys]
        if modifiers and not validvalue(modifiers, registry.modifiers.keys()):
            errors[name] = 'Menus "%s" MODIFIERS value (%s) is invalid.' % (name, modifiers)
            continue

        # update conf value (alos with defaults)
        value.update({
            'MODIFIERS': modifiers,
            'NAME': name,
            'CACHE_TIMEOUT': value.get('CACHE_TIMEOUT', DEFAULT_SCHEME['CACHE_TIMEOUT']),
            'CURRENT': False,
        })

    # raise if errors
    if errors:
        raise ImproperlyConfigured('\n'.join(errors.values()))