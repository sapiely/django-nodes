import copy
import time
from django.core.exceptions import ImproperlyConfigured
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
    discovered = None
    _processor = None
    _meta_data = None
    _navigation_node = None

    def __init__(self):
        self.clear()

    def clear(self):
        self.menus = {}
        self.modifiers = {}

    @property
    def processor(self):
        if not self._processor:
            from .processor import Processor

            self.autodiscover()  # also autodiscover once
            cls = import_path(msettings.PROCESSOR, None)
            if not (isinstance(cls, type) and issubclass(cls, Processor)):
                raise ImproperlyConfigured(
                    "Menus PROCESSOR setting value is incorrect '%s'"
                    " is not Processor subclass" % msettings.PROCESSOR)
            processor = cls(self)
            processor.prepare_menus_settings()

            self._processor = processor
        return self._processor

    @property
    def meta_data(self):
        if not self._meta_data:
            value = msettings.META_DATA
            clslist = ([import_path(c) for c in value]
                       if isinstance(value, (list, tuple,)) else
                       [import_path(value),])
            if clslist and not all(i and isinstance(i, type) for i in clslist):
                raise ImproperlyConfigured('Menus META_DATA value error.')
            if not clslist or not issubclass(clslist[-1], MetaData):
                clslist.append(MetaData)
            if len(clslist) > 1:
                cls = type('MixedMetaData', tuple(clslist), {})
            else:
                cls = clslist[0]
            self._meta_data = cls
        return self._meta_data

    @property
    def navigation_node(self):
        if not self._navigation_node:
            cls = import_path(msettings.NAVIGATION_NODE)
            if not (isinstance(cls, type) and issubclass(cls, NavigationNode)):
                raise ImproperlyConfigured(
                    'Menus NAVIGATION_NODE setting is incorrect.'
                    ' %s is not subclass of NavigationNode'
                    % msettings.NAVIGATION_NODE)
            self._navigation_node = cls
        return self._navigation_node

    def autodiscover(self):
        if self.discovered is True:
            return

        error_timeout = time.time() + 20
        discover_timeout, discover_timeout_step = 5, 0.1
        while True:
            # try to lock autodiscoverer (atomic operation)
            self.discovered, is_locked = (
                (time.time() + discover_timeout, True,)
                if not self.discovered or (self.discovered is not True and
                                           time.time() >= self.discovered) else
                (self.discovered, False,)
            )

            discovered = self.discovered  # save to local thread variable
            if discovered is True:
                return
            elif is_locked:
                break
            elif time.time() < discovered:
                time.sleep(discover_timeout_step)
                continue
            elif time.time() >= timeout:
                raise ImproperlyConfigured('Menus autodiscover timeout error.')

        # import menu modules of defined apps
        for app in msettings.MENUS_APPS:
            __import__(app, {}, {}, ['menu'])

        # register builtin modifiers
        if msettings.BUILTIN_MODIFIERS:
            from . import modifiers
            for m in [getattr(modifiers, i) for i in modifiers.__all__]:
                self.register_modifier(m)

        # register custom modifiers
        if msettings.MODIFIERS:
            for modifier_path in msettings.MODIFIERS:
                modifier = import_path(modifier_path, None)
                if not modifier or not isinstance(modifier, type):
                    raise ImproperlyConfigured(
                        "Menus MODIFIERS value error - '%s' is not a modifier."
                        % modifier_path)
                self.register_modifier(modifier,
                                       replace=msettings.MODIFIERS_REPLACE)
        # release lock and set discovered value
        self.discovered = True

    def register_menu(self, menu):
        assert isinstance(menu, type) and issubclass(menu, Menu)
        menu = menu()
        if menu.namespace in self.menus:
            raise NamespaceAllreadyRegistered(
                'Menu with name "%s" is already registered' % menu.namespace)
        self.menus[menu.namespace] = menu

    def register_modifier(self, modifier, replace=False):
        assert isinstance(modifier, type) and issubclass(modifier, Modifier)
        if modifier.__name__ in self.modifiers and not replace:
            raise ModifierAllreadyRegistered(
                'Modifier with name "%s" is already registered'
                % modifier.__name__)
        self.modifiers[modifier.__name__] = modifier()

    def unregister_modifier(self, modifier):
        assert (isinstance(modifier, type) and issubclass(modifier, Modifier)
                or isinstance(modifier, str))
        if not isinstance(modifier, str):
            modifier = modifier.__name__
        if modifier in self.modifiers:
            self.modifiers.__delitem__(modifier)


# menus classes
class Menu(object):
    """Blank menu class"""
    namespace = None
    weight = 500
    navigation_node_class = None

    def __init__(self):
        if not self.namespace:
            self.namespace = self.__class__.__name__

    def get_navigation_node_class(self):
        return self.navigation_node_class or registry.navigation_node

    def get_nodes(self, request):
        """should return a list of NavigationNode instances"""
        raise NotImplementedError


class Modifier(object):
    """Blank modifier class"""
    modify_event = None  # ONCE, PER_REQUEST, POST_SELECT, DEFAULT

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
    id = None  # only for processor.build_nodes method,
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


class ChainItem:
    title = None
    url = None
    data = None

    def __init__(self, title, url, data=None):
        self.title = title
        self.url = url
        self.data = data or {}


class Chain:
    items = None
    item_class = ChainItem

    def __init__(self, data=None):
        self.items = self.get_chain_items_from_data(data)

    def __len__(self):
        return len(self.items)

    def __add__(self, other):
        return self.add(other, append=True)

    def __iadd__(self, other):
        return self.add(other, append=True, inplace=True)

    def __radd__(self, other):
        return self.add(other, append=False)  # other is not Chain

    def copy(self):
        return copy.deepcopy(self)

    def add(self, other, append=True, inplace=False):
        chain = self if inplace else type(self)()
        items = self.get_chain_items_from_data(other)
        chain.items = self.items + items if append else items + self.items
        return chain

    def get_chain_items_from_data(self, data):
        if not data:
            return []
        if not isinstance(data, (list, tuple,)) or isinstance(data[0], str):
            data = [data]
        items = [self.get_chain_item_from_data(i) for i in data]
        return [i for i in items if i]

    def get_chain_item_from_data(self, data):
        if isinstance(data, NavigationNode):
            item = ChainItem(data.title, data.url, data.data.get('chain_data'))
        elif hasattr(data, 'get_absolute_url'):
            item = ChainItem(str(data), data.get_absolute_url())
        elif isinstance(data, (list, tuple,)) and 2 <= len(data) <= 3:
            item = ChainItem(
                data[0], data[1],
                data[2] if len(data)>2 and isinstance(data[2], dict) else None
            )
        elif isinstance(data, dict) and 'title' in data and 'url' in data:
            item = ChainItem(**data)
        elif not isinstance(data, ChainItem):
            item = None
        return item


class MetaData:
    selected = None
    title = None
    chain = None
    chain_class = Chain

    def __init__(self):
        self.title = []
        self.chain = self.chain_class()


# registry singleton
registry = Registry()
