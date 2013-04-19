from django.utils.encoding import smart_str
from .utils import import_path, check_menus_settings
from .menupool import MenuPool
from . import settings as msettings

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
            menupool = msettings.MENU_POOL and import_path(msettings.MENU_POOL) \
                                            or MenuPool
            self._menupool = menupool(self)
            self.autodiscover() # also autodiscover once

            # check settings correctness
            try:
                check_menus_settings()
            except:
                self._menupool = None
                raise

        return self._menupool

    def autodiscover(self):
        if self.discovered: return
        for app in msettings.MENU_APPS:
            __import__(app, {}, {}, ['menu'])
        self.discovered = True

        # register build in modifiers
        if msettings.BUILDIN_MODIFIERS:
            from . import modifiers
            for m in [getattr(modifiers, i) for i in modifiers.__all__]:
                self.register_modifier(m)

    def register_menu(self, menu):
        assert issubclass(menu, Menu)
        menu = menu()
        if menu.namespace in self.menus:
            raise NamespaceAllreadyRegistered, 'Menu with name "%s" is already ' \
                                               'registered' % menu.namespace
        self.menus[menu.namespace] = menu

    def register_modifier(self, modifier):
        assert issubclass(modifier, Modifier)
        if modifier.__name__ in self.modifiers:
            raise ModifierAllreadyRegistered, 'Modifier with name "%s" is already ' \
                                              'registered' % menu.__name__
        self.modifiers[modifier.__name__] = modifier()

    def unregister_modifier(self, modifier):
        assert issubclass(modifier, Modifier)
        if modifier.__name__ in self.modifiers:
            self.modifiers.__delitem__(modifier.__name__)

    def clear_modifiers(self):
        self.modifiers = {}

# exceptions
class NamespaceAllreadyRegistered(Exception):
    pass

class ModifierAllreadyRegistered(Exception):
    pass

# menus classes
class Menu(object):
    """blank menu class"""
    namespace, index = None, 500

    def __init__(self):
        if not self.namespace:
            self.namespace = self.__class__.__name__

    def get_nodes(self, request):
        """should return a list of NavigationNode instances"""
        raise NotImplementedError

class Modifier(object):
    """blank modifier class"""
    modify_rule = 'every_time' # once, every_time, per_request

    def modify(self, request, nodes, namespace, id, post_cut, meta):
        raise NotImplementedError

    def remove_children(self, node, nodes):
        for n in node.children:
            nodes.remove(n)
            self.remove_children(n, nodes)
        node.children = []

    def remove_branch(self, node, nodes):
        if node.parent:
            node.parent.children.remove(node)
        nodes.remove(node)
        self.remove_children(node, nodes)

    def resort_nodes(self, data):
        nodes = []
        def set_children(node, nodes):
            if not node.children: return
            for n in node.children:
                nodes.append(n)
                set_children(n, nodes)
        for node in data:
            if not node.parent:
                nodes.append(node)
                set_children(node, nodes)
        return nodes

class NavigationNode(object):
    """navigation node class"""

    title               = None
    url                 = None
    id                  = None
    parent_id           = None

    visible             = True
    visible_chain       = True

    parent              = None # do not touch
    namespace           = None
    attr                = None

    meta_title          = None
    meta_keywords       = None
    meta_description    = None

    def __init__(self, title, url, id, parent_id=None,
                  visible=True, visible_chain=True, attr=None,
                   meta_title='', meta_keywords='', meta_description=''):
        self.title              = title
        self.url                = url
        self.url_original       = url

        self.id                 = id
        self.parent_id          = parent_id
        self.children           = [] # do not touch
        self.attr               = attr or {}

        self.visible            = visible
        self.visible_chain      = visible_chain

        self.meta_title         = meta_title
        self.meta_keywords      = meta_keywords
        self.meta_description   = meta_description

    def __repr__(self):
        return "<Navigation Node: %s>" % smart_str(self.title)

    def get_descendants(self):
        nodes = []
        for node in self.children:
            nodes.append(node)
            nodes += node.get_descendants()
        return nodes