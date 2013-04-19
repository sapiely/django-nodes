from django.conf import settings

"""
# menus sample settings
MENUS_APPS = ['content',]
MENUS_BUILDIN_MODIFIERS = True
MENUS_MENUPOOL = 'application.menu.MenuPool'
MENUS_ROUTES = (
    ('^(/some/url/|/another/)', 'simple',),
)
MENUS = {
    'default': {
        'MENUS': ['NodeMainMenu', 'TestSideMenu',],
        'MODIFIERS': ['NavExtender', 'LoginRequired', 'Jump',
                      'Namespace', 'Level',],
        'CACHE_TIMEOUT': 600,
    },
    'simple': {
        'MENUS': ['TestSideMenu',],
        'MODIFIERS': None, # [] for empty modifiers
        'CACHE_TIMEOUT': 600,
    },
}
"""

DEFAULT_SCHEME = {
    'MODIFIERS': ['NavExtender', 'LoginRequired', 'Jump', 'Namespace', 'Level',],
    'CACHE_TIMEOUT': 600,
}

MENU_APPS           = getattr(settings, 'MENUS_APPS', None)
BUILDIN_MODIFIERS   = getattr(settings, 'MENUS_BUILDIN_MODIFIERS', True)
MENU_POOL           = getattr(settings, 'MENUS_MENUPOOL', None)
MENU_CONF           = getattr(settings, 'MENUS', None)
MENU_ROUTES         = getattr(settings, 'MENUS_ROUTES', None) or []