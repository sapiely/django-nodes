from django.conf import settings

"""
# menus sample settings
MENUS_APPS = ['content',]
MENUS_BUILTIN_MODIFIERS = True

DEFAULT_PROCESSOR = 'application.menu.Processor'
MENUS_NODE = 'application.menu.NavigationNode'
MENUS_METADATA = 'application.menu.MetaData'

#MENUS_ROUTES = (
#    ('^(/some/url/|/another/)', 'simple',),
#)
MENUS = {
    'default': {
        'MENUS': ['NodeMainMenu', 'TestSideMenu',],
        'MODIFIERS': {
            'default': ['NavigationExtender', 'AuthVisibility',
                        'Jump', 'Namespace', 'Level',],
            'minimal': ['Jump', 'Level',],
            'filters': ['Jump', 'Filter', 'CutLevels', 'Level',],
        }
        'CACHE_TIMEOUT': 600,
    },
    'simple': {
        'MENUS': ['TestSideMenu',],
        'MODIFIERS': None, # [] for empty modifiers
        'CACHE_TIMEOUT': 600,
        'ROUTE': '^(/some/url/|/another/)',
    },
}
"""

DEFAULT_SCHEME = {
    'MODIFIERS': [
        'NavigationExtender', 'AuthVisibility', 'Jump',
        'Root', 'Namespace', 'Level', 'MetaDataProcessor',
        'PositionalMarker', 'CutLevels', # 'Filter',
    ],
    'CACHE_TIMEOUT': 600,
}
DEFAULT_META_DATA = 'nodes.base.MetaData'
DEFAULT_PROCESSOR = 'nodes.processor.Processor'
DEFAULT_NAVIGATION_NODE = 'nodes.base.NavigationNode'

MENU_APPS           = getattr(settings, 'MENUS_APPS', None)
BUILTIN_MODIFIERS   = getattr(settings, 'MENUS_BUILTIN_MODIFIERS', True)
PROCESSOR           = getattr(settings, 'MENUS_PROCESSOR', DEFAULT_PROCESSOR)
META_DATA           = getattr(settings, 'MENUS_META_DATA', DEFAULT_META_DATA)
NAVIGATION_NODE     = getattr(settings, 'MENUS_NAVIGATION_NODE',
                              DEFAULT_NAVIGATION_NODE)
MENUS               = getattr(settings, 'MENUS', None)



"""
# menus sample settings
MENUS_APPS = ['content',]
MENUS_BUILTIN_MODIFIERS = True
DEFAULT_PROCESSOR = 'application.menu.Processor'
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
PROCESSOR           = getattr(settings, 'DEFAULT_PROCESSOR', None)
MENUS               = getattr(settings, 'MENUS', None)
"""
