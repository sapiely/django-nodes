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
        self._menupool = None

    @property
    def menupool(self):
        if not self._menupool:
            menupool = import_path(
                msettings.MENU_POOL or msettings.DEFAULT_MENU_POOL)
            self._menupool = menupool(self)
            self.autodiscover() # also autodiscover once

            # prepare and check settings correctness
            try:
                self._menupool.prepare_menus_settings()
            except:
                self._menupool = None
                raise

        return self._menupool

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

    def __init__(self):
        if not self.namespace:
            self.namespace = self.__class__.__name__

    def get_navigation_node_class(self):
        return import_path(msettings.NAVIGATION_NODE
                           or msettings.DEFAULT_NAVIGATION_NODE)

    def get_nodes(self, request):
        """should return a list of NavigationNode instances"""
        raise NotImplementedError


class Modifier(object):
    """blank modifier class"""
    modify_event = None # ONCE, PER_REQUEST, POST_SELECT, DEFAULT

    def modify(self, request, data, meta, **kwargs):
        """
        This method takes nodes data dict (
            {"nodes": nodes, "selected": selected,}
        ) and should update "nodes" value, if required.
        Nodes should be always returned in linear format.
        """
        raise NotImplementedError

    def get_descendants_length(self, node, length=0):
        if node.children:
            for child in node.children:
                length += 1 + self.get_descendants_length(child)
        return length

    def get_descendants(self, node, nodes=None):
        nodes = nodes or []
        for n in node.children:
            nodes.append(n)
            if n.children:
                nodes = self.get_descendants(n, nodes=nodes)
        return nodes

    def format_nodes(self, nodes, linear=True):
        # get hierarchical nodes
        nodes = [node for node in nodes if not node.parent]

        # hierarchical (not linear)
        if not linear:
            return nodes

        # linear
        final = []
        for node in nodes:
            final += [node] + self.get_descendants(node)
        return final


class NavigationNode(object):
    """Navigation node class"""

    title = None
    url = None
    namespace = None
    data = None

    id = None
    parent = None
    children = None

    visible = True
    selected = False
    active = True
    modified = False

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

    def get_descendants(self):
        nodes = []
        for node in self.children:
            nodes += [node] + node.get_descendants()
        return nodes


class MetaData(object):
    selected = None
    chain = None
    title = None

    def __init__(self):
        self.chain = []
        self.title = []
