from django.conf import settings

"""
# menus sample settings
MENUS_APPS = ['content',]
MENUS_BUILTIN_MODIFIERS = True

MENUS_MENUPOOL = 'application.menu.MenuPool'
MENUS_NODE = 'application.menu.NavigationNode'
MENUS_METADATA = 'application.menu.MetaData'

MENUS_ROUTES = (
    ('^(/some/url/|/another/)', 'simple',),
)
MENUS = {
    'default': {
        'MENUS': ['NodeMainMenu', 'TestSideMenu',],
        'MODIFIERS': {
            'default': ['NavigationExtender', 'LoginRequired', 'Jump', 'Namespace', 'Level',],
            'minimal': ['Jump', 'Level',],
            'filters': ['Jump', 'Filter', 'CutLevels', 'Level',],
        }
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
    'MODIFIERS': [
        'NavigationExtender', 'LoginRequired', 'Jump',
        'Root', 'Namespace', 'Level', 'MetaDataProcessor',
        'PositionalFlagsMarker', 'CutLevels', # 'Filter',
    ],
    'CACHE_TIMEOUT': 600,
}
DEFAULT_METADATA = 'menus.base.MetaData'
DEFAULT_MENU_POOL = 'menus.menupool.MenuPool'
DEFAULT_NAVIGATION_NODE = 'menus.base.NavigationNode'

MENU_APPS           = getattr(settings, 'MENUS_APPS', None)
BUILTIN_MODIFIERS   = getattr(settings, 'MENUS_BUILTIN_MODIFIERS', True)
MENU_POOL           = getattr(settings, 'MENUS_MENUPOOL', None)
META_DATA           = getattr(settings, 'MENUS_METADATA', None)
NAVIGATION_NODE     = getattr(settings, 'MENUS_NAVIGATION_NODE', None)
MENU_CONF           = getattr(settings, 'MENUS', None)
MENU_ROUTES         = getattr(settings, 'MENUS_ROUTES', None) or []

"""
# menus sample settings
MENUS_APPS = ['content',]
MENUS_BUILTIN_MODIFIERS = True
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

"""
DEFAULT_SCHEME = {
    'MODIFIERS': ['NavExtender', 'LoginRequired', 'Jump', 'Namespace', 'Level',],
    'CACHE_TIMEOUT': 600,
}

MENU_APPS           = getattr(settings, 'MENUS_APPS', None)
BUILTIN_MODIFIERS   = getattr(settings, 'MENUS_BUILTIN_MODIFIERS', True)
MENU_POOL           = getattr(settings, 'MENUS_MENUPOOL', None)
MENU_CONF           = getattr(settings, 'MENUS', None)
MENU_ROUTES         = getattr(settings, 'MENUS_ROUTES', None) or []
"""
