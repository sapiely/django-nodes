import copy
import re
import urlparse
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import get_language
from .base import DEFAULT, ONCE, PER_REQUEST, POST_SELECT
from .utils import import_path
from . import settings as msettings


class MenuPool(object):

    # methods that are expected to be extended if required:
    #   router - menuconf router by request
    #   check_node_url_with_domain - check urls with domain specified
    #   compare_path - compare two paths by length, get/hash existance, ect
    #   cache_key - cache name generator for confname
    #   prepare_menus_settings - prepare settings value

    registry = None

    def __init__(self, registry):
        self.registry = registry
        self._modifiers = {}

    def router(self, request):
        """
        Simple router implementaion, based on url regexps.
        If you need more complex validation, please update this method.
        """
        for route, conf in msettings.MENU_ROUTES:
            if re.match(route, request.path):
                return conf

        return 'default'

    def menuconf(self, request, name=None):
        """Get menuconf value, call router if required (once)"""

        # get menu configuration data (dict value expected as valid)
        # also if menuconf is dict -> request is already meta-processed
        if isinstance(name, dict):
            return name

        # update request with meta
        self.add_nodes_to_request(request)

        # call router once per request
        if not hasattr(request.nodes, '_menuconf'):
            request.nodes._menuconf_selected = self.router(request)
            request.nodes._menuconf = {}

        # get menuconf and cache it
        name = name or request.nodes._menuconf_selected
        conf = request.nodes._menuconf.get(name, None)
        if not conf:
            conf = msettings.MENU_CONF.get(name, None)
            if conf is None:
                raise ValueError('Menus menuconf invalid name (%s).' % name)

            conf['SELECTED'] = name == request.nodes._menuconf_selected
            request.nodes._menuconf[name] = conf

        return conf

    def cache_key(self, request=None, menuconf=None,
                  lang=None, site_id=None, extra=None, **kwargs):
        """
        Generate cache_key by request and menuconf data, by lang and site
        note: extra should be list or tuple, any item should be ascii string
        """
        lang = lang or get_language()
        site_id = site_id or get_current_site(None).pk
        extra = '_'.join(map(str, extra)) if extra else ''
        return 'nodes_%s_%s_%s%s_cache' % (menuconf['NAME'],
                                           lang, site_id, extra)

    def post_build_data_handler(self, menuconf, nodes, request):
        """
        By default return {"nodes": nodes, "paths": paths,}.
        Paths using for indexed search of selected node. If you wll find
        faster method, you can override all behaviour, including selected node
        decetion.
        All result data must be serializable.
        """
        nodes.update({'paths': self.build_paths(nodes['nodes']),})

    def get_nodes(self, menuconf, request,
                  modifiers=None, init_only=False, **kwargs):
        """Generate nodes by menu confname."""

        menuconf = self.menuconf(request, name=menuconf)

        # cache requested menuconf nodes in request object
        nodes = getattr(request.nodes, '_menus', {}).get(menuconf['NAME'], None)
        if nodes is None:
            request.nodes._menus = getattr(request.nodes, '_menus', {})

            # longtime between-request cached code
            cache_key = self.cache_key(request=request, menuconf=menuconf)
            nodes = cache.get(cache_key, None)
            if not nodes:
                nodes = self.build_nodes(request, menuconf['MENUS'])
                nodes = {'nodes': nodes, 'selected': None,}
                self.apply_modifiers(menuconf, nodes, request, modify_event=ONCE)
                self.post_build_data_handler(menuconf, nodes, request)
                cache.set(cache_key, nodes, menuconf['CACHE_TIMEOUT'])

            # per-request cached code (PER_REQUEST)
            self.apply_modifiers(menuconf, nodes, request, modify_event=PER_REQUEST)

            # selected node related code
            # check - does menu routed (SELECTED) or requested directly
            # only SELECTED menuconf mark as selected
            # todo: may be add CHECK_SELECTION param to conf?
            if menuconf['SELECTED']:
                self._mark_selected(request, nodes)

            # per-request cached code (POST_SELECT)
            self.apply_modifiers(menuconf, nodes, request, modify_event=POST_SELECT)

            request.nodes._menus[menuconf['NAME']] = nodes

        if init_only:
            return

        # clone nodes and run apply_modifiers with DEFAULT modify_event
        nodes = copy.deepcopy(nodes)
        self.apply_modifiers(menuconf, nodes, request, modify_event=DEFAULT,
                             modifiers=modifiers, kwargs=kwargs)

        # return nodes in hierarchical format
        nodes['nodes'] = [i for i in nodes['nodes'] if not i.parent]
        return nodes

    def apply_modifiers(self, menuconf, nodes, request, modify_event=DEFAULT,
                        modifiers=None, meta=None, kwargs=None):
        """
        Modify nodes by modifiers, related to menu confname.modifiers.
        Params:
            nodes - dict with nodes and selected node value, also can
                contain any other user information (by default it contains
                paths for indexed search of selected node). Nodes structure
                see in get_nodes method.

            modify_event - event, after which modifiers called. Builtin values:
                ONCE - run once, before caching nodes data between requests,
                PER_REQUEST - run every request once, before any other no-ONCE,
                POST_SELECT - run every request after selected node is marked,
                DEFAULT - run every time get_nodes called with different args.

            meta - additional dict with some runtime tips, which helps next
                modifiers speed-up their processing. Builtin keys:

                modify_event - event value apply_modifiers called with,
                rebuld_mode - in ONCE and PER_REQUEST events means that
                    apply_modifiers executed second or more time,
                modified_ancestors - should be set to True by modifier,
                    if any parent propery value modified
                modified_descendants - should be set to True by modifier,
                    if any children propery values modified
                modified_structure - should be set to True by modifier,
                    if modifier changes original structure (for example,
                    Namespace modifier set this param for Level modifier).
                modified_nodes - should be set to True by modifier,
                    if any node was dynamically activated/generated.

                User can provide any other keys to your own modifiers.
        """

        # process arguments
        menuconf, kwargs = self.menuconf(request, name=menuconf), kwargs or {}
        meta = meta or {
            'modify_event': None, 'rebuld_mode': False,
            'modified_ancestors': False, 'modified_nodes': False,
            'modified_structure': False, 'modified_descendants': False,
        }
        meta.update(modify_event=modify_event)

        # get (cached) value of modifiers by menuconf name and modifiers group
        modifconf = modifiers or 'default'
        modifname = '%s.%s' % (menuconf['NAME'], modifconf,)
        modifiers = self._modifiers.get(modifname, None)
        if not modifiers:
            modifiers = [self.registry.modifiers[mod]
                         for mod in menuconf['MODIFIERS'][modifconf]]
            self._modifiers[modifname] = modifiers

        # process
        for modifier in modifiers:
            if modify_event & modifier.modify_event:
                modifier.modify(request, nodes, meta, **kwargs)

    # raw menus nodes list generator
    def build_nodes(self, request, menus):
        """build raw full nodes array (linear) with parent links"""
        final_nodes, ignored_nodes = {'ids':{}, 'nodes':[],}, {}

        # get menus from registry and sort by weight attr desc
        menus = [self.registry.menus[m] for m in menus]
        menus = sorted(menus, cmp=lambda x,y: cmp(x.weight, y.weight))

        # fetch all nodes from all menus
        for menu in menus:
            nodes, last = menu.get_nodes(request), None
            for node in nodes:
                # set namespace attr and indexes (default: menu class name)
                node.namespace = node.namespace or menu.namespace
                final_nodes['ids'][node.namespace] = final_nodes['ids'].get(node.namespace, [])
                ignored_nodes[node.namespace] = ignored_nodes.get(node.namespace, [])

                # ignore nodes with dublicated ids
                if node.id in final_nodes['ids'][node.namespace]:
                    continue
                # process all childs
                if node.parent:
                    found = False
                    # ignore node if parent also ignored
                    if node.parent in ignored_nodes[node.namespace]:
                        ignored_nodes[node.namespace].append(node.id)
                        continue
                    # try to find parent in ancestors chain (optimization)
                    if last:
                        n = last
                        while n:
                            if n.namespace == node.namespace and n.id == node.parent:
                                node.parent, found, n = n, True, None
                            else:
                                n = n.parent or None
                    # search parent directrly (slowly)
                    if not found:
                        for n in nodes:
                            if n.namespace == node.namespace and n.id == node.parent:
                                node.parent, found = n, True
                    # if parent is found - append node to "brothers", else ignore invalid
                    if found:
                        node.parent.children.append(node)
                    else:
                        ignored_nodes[node.namespace].append(node.id)
                        continue
                # append node and it id to main list
                final_nodes['nodes'].append(node)
                final_nodes['ids'][node.namespace].append(node.id)
                # last node for search in ancestors
                last = node

        # reindex ids in nodes array
        final_nodes, i = final_nodes['nodes'], 1
        for node in final_nodes:
            node.id, i = i, i+1
        return final_nodes

    # selection speedup by indexed search (with paths dict)
    def check_node_url_with_domain(self, domain, node):
        return False

    def compare_path(self, path, node, ppath, pnode):
        """Return True, if we should replace old item by new one."""
        # Shorter path better.
        if path != ppath:
            return path < ppath

        # Greater weight better.
        wnew = node.data.get('menu_item_weight', 0)
        wold = pnode.data.get('menu_item_weight', 0)
        if wnew != wold:
            return wnew > wold

        return False

    def _get_path(self, node):
        p = urlparse.urlparse(node.url_original)
        if p.netloc and not self.check_node_url_with_domain(p.netloc, node):
            return None
        return p.path.strip('/').split('/')

    def build_paths(self, nodes):
        data = {}
        for node in nodes:
            path = self._get_path(node)
            # ignore nodes with denied domain name and/or empty path
            if not path:
                continue

            for item in ['/'.join(path[:i]) for i in range(1, len(path)+1)]:
                if data.has_key(item):
                    # check this node is better match than previous
                    ppath = self._get_path(data[item])
                    if self.compare_path(path, node, ppath, data[item]):
                        data[item] = node
                else:
                    # link path with node
                    data[item] = node
        return data

    def _mark_selected(self, request, data):
        """mark current node as selected (indexed search in paths)"""

        # id dict for speedup (indexed) node search
        nodekeys = dict((n.id, None) for n in data['nodes'])
        paths = data['paths']

        path = request.path.strip('/').split('/')
        for pkey in ['/'.join(path[:-i or None]) for i in range(0, len(path))]:
            selected = paths.get(pkey, None)
            if selected:
                # check selected for existance in morphed with
                # per_request modifiers nodes list (auth visibility, ect)
                if not selected.id in nodekeys:
                    continue

                selected.selected = True
                data.update(selected=selected)
                break

    def add_nodes_to_request(self, request):
        """prepare request for menus processing"""
        if not hasattr(request, 'nodes'):
            metadata = import_path(msettings.META_DATA
                                   or msettings.DEFAULT_METADATA)
            request.nodes = metadata()

    def prepare_menus_settings(self):
        """prepare menus settings validity"""

        # get menu settings for check
        MENU_CONF = msettings.MENU_CONF
        DEFAULT_SCHEME = msettings.DEFAULT_SCHEME
        MENU_ROUTES = msettings.MENU_ROUTES

        # check MENU_CONF
        # todo: may be someway disable menus if improperly configured
        if not isinstance(MENU_CONF, dict) or not MENU_CONF.has_key('default'):
            raise ImproperlyConfigured('Menus "MENU_CONF" setting value'
                                       ' is empty/incorrect or not contains'
                                       ' "default" key.')

        validvalue = lambda val, chk: (set(val).__len__() == val.__len__()
                                       and all([v in chk for v in val]))

        errors = {}
        for name, value in MENU_CONF.items():
            # check menus value
            menus = value.get('MENUS', None)
            if not menus or not validvalue(menus, self.registry.menus.keys()):
                errors[name] = ('Menus "%s" MENUS value (%s)'
                                ' is invalid.' % (name, menus))
                continue

            # check modifiers value
            modifiers = value.get('MODIFIERS', None)
            modkeys, invalid = self.registry.modifiers.keys(), False

            # prepare modifiers value:
            #   convert list/tuple to dict with "default" key
            #   convert any other type to default value
            #   add default key, if it does not exists in dict value
            if isinstance(modifiers, (list, tuple,)):
                modifiers = {'default': modifiers,}
            if not isinstance(modifiers, dict):
                modifiers = {'default': [m for m in DEFAULT_SCHEME['MODIFIERS']
                                         if m in modkeys],}
            if 'default' not in modifiers:
                modifiers['default'] = [m for m in DEFAULT_SCHEME['MODIFIERS']
                                        if m in modkeys]

            for mname, mvalue in modifiers.items():
                if mvalue and not validvalue(mvalue, modkeys):
                    errors[name] = ('Menus "%s" MODIFIERS "%s" value (%s)'
                                    ' is invalid.' % (name, mname, mvalue,))
                    invalid = True
            if invalid:
                continue


            # update conf value (alos with defaults)
            value.update({
                'MODIFIERS': modifiers,
                'NAME': name,
                'CACHE_TIMEOUT': value.get('CACHE_TIMEOUT',
                                           DEFAULT_SCHEME['CACHE_TIMEOUT']),
                'SELECTED': False,
            })

        if errors:
            raise ImproperlyConfigured('\n'.join(errors.values()))

        # check MENU_ROUTES TODO? should it be requeired
        if MENU_ROUTES and not isinstance(MENU_ROUTES, (list, tuple,)):
            raise ImproperlyConfigured('Menus "MENU_ROUTES" setting value is incorrect,'
                                       ' it should be (list, tuple) or empty.')

        errors = []
        for route in MENU_ROUTES:
            if not len(route) == 2 or \
                not isinstance(route[0], basestring) or \
                not route[1] in MENU_CONF.keys():

                errors.append('Incorrect menu route value (%s). Each route should be'
                              ' instance of list or tupe, have len equal 2, contain'
                              ' matching pattern (string, first item) and point'
                              ' to existing menu_conf item (second item).' % str(route))

        if errors:
            raise ImproperlyConfigured('\n'.join(errors))
