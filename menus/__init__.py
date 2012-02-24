from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

setting_keys = ['MENUS_APPS', 'MENUS_CACHE_DURATION',]
if filter(lambda x: x is None, [getattr(settings, key, None) for key in setting_keys]):
    raise ImproperlyConfigured('Menus app require setting params defined: %s.' % (', ').join(setting_keys))
    
VERSION = (0, 1, 27)