from django.conf import settings


DEFAULT_SCHEME = {
    'MODIFIERS': [
        'NavigationExtender', 'AuthVisibility', 'Jump',
        'Root', 'Namespace', 'Level', 'MetaDataProcessor',
        'PositionalMarker', 'CutLevels',  # 'Filter',
    ],
    'CACHE_TIMEOUT': 600,
}
DEFAULT_META_DATA = 'nodes.base.MetaData'
DEFAULT_PROCESSOR = 'nodes.processor.Processor'
DEFAULT_NAVIGATION_NODE = 'nodes.base.NavigationNode'

MENUS_APPS = getattr(settings, 'MENUS_APPS', [])
MENUS = getattr(settings, 'MENUS', None)

BUILTIN_MODIFIERS = getattr(settings, 'MENUS_BUILTIN_MODIFIERS', True)
MODIFIERS_REPLACE = getattr(settings, 'MENUS_MODIFIERS_REPLACE', True)
MODIFIERS = getattr(settings, 'MENUS_MODIFIERS', None)

PROCESSOR = getattr(settings, 'MENUS_PROCESSOR', DEFAULT_PROCESSOR)
META_DATA = getattr(settings, 'MENUS_META_DATA', DEFAULT_META_DATA)
NAVIGATION_NODE = getattr(settings, 'MENUS_NAVIGATION_NODE',
                          DEFAULT_NAVIGATION_NODE)

METATAGS_METATAG_MODEL = getattr(settings, 'MENUS_METATAGS_METATAG_MODEL', None)
METATAGS_CONTAINER_MODEL = getattr(settings, 'MENUS_METATAGS_CONTAINER_MODEL', None)
METATAGS_BUILTIN_MODELS = getattr(settings, 'MENUS_METATAGS_BUILTIN_MODELS', False)
METATAGS = getattr(settings, 'MENUS_METATAGS', None)


# Full featured menus settings sample
# -----------------------------------
"""
# Nodes settings
MENUS_APPS = ['pages', 'accounts', 'testapp',]
MENUS_BUILTIN_MODIFIERS = True
MENUS_MODIFIERS_REPLACE = True
MENUS_MODIFIERS = (
    'nodes.contrib.metatags.nodes.MetaDataProcessor',  # replace builtin
    'main.nodes.AuthGroupVisibility',
)
MENUS_META_DATA = (
    'nodes.contrib.metatags.nodes.MetaTagsMetaDataMixin',  # add metatags mixin
    'main.nodes.MetaData',
)
MENUS_PROCESSOR = 'main.nodes.Processor'
MENUS_NAVIGATION_NODE = 'main.menu.NavigationNode'
MENUS = {
    'default': {
        'MENUS': ['PageMenu', 'CategoryMenu',],
        'MODIFIERS': {
            'default': ['NavigationExtender', 'AuthGroupVisibility',
                        'Jump', 'Namespace', 'Level', 'MetaDataProcessor',],
            'minimal': ['Jump', 'Level',],
            'filters': ['Jump', 'Filter', 'CutLevels', 'Level',],
        }
        'CACHE_TIMEOUT': 300,
    },
    'account': {
        'MENUS': ['AccountMenu',],
        'MODIFIERS': ['Jump', 'CutLevels', 'Level', 'MetaDataProcessor',],
        'CACHE_TIMEOUT': 1200,
        'ROUTE': '^/(accounts|order|clubs/achievements)/',
    },
    'simple': {
        'MENUS': ['TestSideMenu',],
        'MODIFIERS': None,  # [] for empty modifiers
        'CACHE_TIMEOUT': 600,
        'ROUTE': '^/(some/url|another)/',
    },
}
MENUS_METATAGS_METATAG_MODEL = 'main.MetaTag'
MENUS_METATAGS_CONTAINER_MODEL = 'main.MetaTagsContainer'
MENUS_METATAGS = {
    'description': 'NameContentStringMetaTag',
    'keywords': 'NameContentCommaSpaceSeparatedValueTag',
    'generator': 'NameContentListMetaTag',
    'og': 'PropertyContentDictMetaTag',
    'twitter': 'NameContentDictMetaTag',
}
"""
