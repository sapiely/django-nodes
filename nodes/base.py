from .utils import import_path
from . import settings as msettings


ONCE = 1
PER_REQUEST = 2
POST_SELECT = 4
DEFAULT = 8


# exceptions
class NamespaceAllreadyRegistered(Exception):
    pass


class ModifierAllreadyRegistered(Exception):
    pass


# registry
class Registry(object):
    def __init__(self):
        self.menus = {}
        self.modifiers = {}
        self.discovered = False
        self._processor = None

    @property
    def processor(self):
        if not self._processor:
            processor = import_path(msettings.PROCESSOR)
            self._processor = processor(self)
            self.autodiscover() # also autodiscover once

            # prepare and check settings correctness
            try:
                self._processor.prepare_menus_settings()
            except:
                self._processor = None
                raise

        return self._processor

    def autodiscover(self):
        if self.discovered:
            return
        for app in msettings.MENU_APPS:
            __import__(app, {}, {}, ['menu'])
        self.discovered = True

        # register build in modifiers
        if msettings.BUILTIN_MODIFIERS:
            from . import modifiers
            for m in [getattr(modifiers, i) for i in modifiers.__all__]:
                self.register_modifier(m)

    def register_menu(self, menu):
        assert issubclass(menu, Menu)
        menu = menu()
        if menu.namespace in self.menus:
            raise (NamespaceAllreadyRegistered,
                   'Menu with name "%s" is already registered'
                   % menu.namespace)
        self.menus[menu.namespace] = menu

    def register_modifier(self, modifier):
        assert issubclass(modifier, Modifier)
        if modifier.__name__ in self.modifiers:
            raise (ModifierAllreadyRegistered,
                   'Modifier with name "%s" is already registered'
                   % modifier.__name__)
        self.modifiers[modifier.__name__] = modifier()

    def unregister_modifier(self, modifier):
        assert issubclass(modifier, Modifier)
        if modifier.__name__ in self.modifiers:
            self.modifiers.__delitem__(modifier.__name__)

    def clear_modifiers(self):
        self.modifiers = {}


# menus classes
class Menu(object):
    """blank menu class"""
    namespace = None
    weight = 500
    navigation_node_class = None

    def __init__(self):
        if not self.namespace:
            self.namespace = self.__class__.__name__

    def get_navigation_node_class(self):
        return self.navigation_node_class or import_path(
            msettings.NAVIGATION_NODE)

    def get_nodes(self, request):
        """should return a list of NavigationNode instances"""
        raise NotImplementedError


class Modifier(object):
    """blank modifier class"""
    modify_event = None # ONCE, PER_REQUEST, POST_SELECT, DEFAULT

    def modify(self, request, data, meta, **kwargs):
        """
        This method takes nodes data dict (
            {"nodes": nodes, "selected": selected, 'chain': chain,}
        ) and should update "nodes" value, if required.
        Nodes should be always returned in hierarchical format.
        """
        raise NotImplementedError


class NavigationNode(object):
    """Navigation node class"""

    title = None
    url = None
    namespace = None
    data = None

    parent = None
    children = None
    id = None   # only for processor.build_nodes method,
                # should be unique within each Menu data definition

    visible = True
    selected = False

    def __init__(self, title, url, id, parent=None, visible=True,
                 data=None, **kwargs):
        self.title = title
        self.url = self.url_original = url
        self.data = data or {}

        self.id = id
        self.parent = parent
        self.children = []

        self.visible = visible

    def __repr__(self):
        return u'<Navigation Node: %s>' % self.title

    def on_selected(self, menuconf, nodes, request):
        return False


class MetaData(object):
    selected = None
    chain = None
    title = None

    def __init__(self):
        self.chain = []
        self.title = []
        self.keywords = []  # tobe deleted
        self.description = []  # tobe deleted
