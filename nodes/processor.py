import copy
import re
from urllib import parse
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.shortcuts import get_current_site
from django.utils.translation import get_language
from .base import Menu, DEFAULT, ONCE, PER_REQUEST, POST_SELECT
from .utils import import_path, tgenerator
from . import settings as msettings


class Processor(object):
    # methods that are expected to be extended if required:
    #   router - menuconf router
    #   cache_key - cache name generator for confname
    #   post_build_data_handler - update data after ONCE
    #   check_node_url_with_domain - check urls with specified domain
    #   compare_paths - compare two paths by length, get/hash existance, ect

    registry = None

    def __init__(self, registry):
        self.registry = registry
        self._modifiers = {}

    def router(self, request):
        """
        Simple router implementaion, based on url regexps.
        If you need more complex validation, please update this method.
        """
        if not hasattr(self, '_ROUTES'):
            self._ROUTES = [(name, conf['ROUTE'])
                            for name, conf in msettings.MENUS.items()
                            if conf.get('ROUTE', None)] or None

        if self._ROUTES:
            for name, route in self._ROUTES:
                if re.match(route, request.path):
                    return name

        return 'default'

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
            conf = msettings.MENUS.get(name, None)
            if conf is None:
                raise ValueError('Menus menuconf invalid name (%s).' % name)

            conf['SELECTED'] = name == request.nodes._menuconf_selected
            request.nodes._menuconf[name] = conf

        return conf

    # Nodes processing methods
    # ------------------------
    def get_nodes(self, menuconf, request,
                  modifiers=None, init_only=False, **kwargs):
        """Generate nodes by menu confname."""

        menuconf = self.menuconf(request, name=menuconf)

        # cache requested menuconf nodes in request object
        nodes = getattr(request.nodes, 'menus', {}).get(menuconf['NAME'], None)
        if nodes is None:
            request.nodes.menus = getattr(request.nodes, 'menus', {})

            cache_key = self.cache_key(request=request, menuconf=menuconf)
            cache_required = False
            rebuild_mode = False
            rebuild_countdown = 10

            while rebuild_countdown:
                rebuild_countdown -= 1
                meta = {'rebuild_mode': rebuild_mode,}
                nodes = cache.get(cache_key, None) if nodes is None else nodes

                if nodes is None:
                    nodes = self.build_nodes(request, menuconf['MENUS'])
                    nodes = {'nodes': nodes, 'selected': None, 'chain': None,}
                    cache_required = True

                # running once cached code (ONCE)
                self.apply_modifiers(menuconf, nodes, request,
                                     modify_event=ONCE, meta=meta)
                self.post_build_data_handler(menuconf, nodes, request, meta)

                if cache_required and not rebuild_mode:
                    cache.set(cache_key, nodes, menuconf['CACHE_TIMEOUT'])

                # per-request cached code (PER_REQUEST)
                self.apply_modifiers(menuconf, nodes, request,
                                     modify_event=PER_REQUEST, meta=meta)

                # selected node related code
                # check - does menu routed (SELECTED) or requested directly
                # only SELECTED menuconf mark as selected
                # todo: may be add CHECK_SELECTION param to conf?
                if menuconf['SELECTED']:
                    selected, chain = self.search_selected(request, nodes)
                    rebuild_mode = (
                        selected and not getattr(selected, 'rebuilt', None) and
                        selected.on_selected(menuconf, nodes, request))
                    if rebuild_mode:
                        selected.selected, selected.rebuilt = False, True
                        continue

                    nodes.update(selected=selected, chain=chain)
                break

            if not rebuild_countdown:
                raise Exception('Nodes: too deep rebuild cycle.')

            # per-request cached code (POST_SELECT)
            self.apply_modifiers(menuconf, nodes, request,
                                 modify_event=POST_SELECT)

            request.nodes.menus[menuconf['NAME']] = nodes

        if init_only:
            return

        # clone nodes and run apply_modifiers with DEFAULT modify_event
        nodes = copy.deepcopy(nodes)
        self.apply_modifiers(menuconf, nodes, request, modify_event=DEFAULT,
                             modifiers=modifiers, kwargs=kwargs)

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
                rebuild_mode - in ONCE and PER_REQUEST events means that
                    apply_modifiers executed second or more time,
                modified_ancestors - should be set to True by modifier,
                    if any parent value modified
                modified_descendants - should be set to True by modifier,
                    if any children value modified

                User can provide any other keys to your own modifiers.
        """

        # process arguments
        menuconf, kwargs = self.menuconf(request, name=menuconf), kwargs or {}
        meta = dict({
            'modify_event': None, 'rebuild_mode': False,
            'modified_ancestors': False, 'modified_descendants': False,
        }, **dict(meta or {}, modify_event=modify_event))

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
        """Build raw nodes tree"""
        final, ids, ignored = [], {}, {}

        # get menus from registry and sort by weight attr asc
        menus = [m if isinstance(m, Menu) else self.registry.menus[m]
                 for m in menus]
        menus = sorted(menus, key=lambda x: x.weight)

        # fetch all nodes from all menus
        for menu in menus:
            nodes = menu.get_nodes(request)
            for node in nodes:
                # set namespace attr, default: menu class name
                node.namespace = node.namespace or menu.namespace
                ids[node.namespace] = ids.get(node.namespace, [])
                ignored[node.namespace] = ignored.get(node.namespace, [])

                # ignore nodes with duplicated ids
                if node.id in ids[node.namespace]:
                    continue
                # process all childs
                if node.parent:
                    found = False
                    # ignore node if parent also ignored
                    if node.parent in ignored[node.namespace]:
                        ignored[node.namespace].append(node.id)
                        continue
                    # search parent
                    for n in nodes:
                        if n.namespace == node.namespace and n.id == node.parent:
                            node.parent, found = n, True
                            break
                    # append found node to its "brothers" or ignore
                    if found:
                        node.parent.children.append(node)
                    else:
                        ignored[node.namespace].append(node.id)
                        continue
                # append node and it id to main list
                final.append(node)
                ids[node.namespace].append(node.id)

        return [i for i in final if not i.parent]

    def post_build_data_handler(self, menuconf, nodes, request, meta):
        """
        By default updates nodes with {"paths": paths,}.
        Paths using for indexed search of selected node. If you will find
        faster method, you can override all behaviour, including selected node
        detection.
        All result data must be serializable.
        """
        if not meta['rebuild_mode']:
            nodes.update({'paths': self.build_paths(nodes['nodes']),})

    # Selection speedup by indexed search (with paths dict)
    # -----------------------------------------------------
    def check_node_url_with_domain(self, domain, node):
        return False

    def compare_paths(self, node, prevnode):
        """
        Return True, if we should replace old item by new one.
        Greater weight better.
        """
        return node.data.get('weight', 500) >= prevnode.data.get('weight', 500)

    def get_path(self, node):
        p = parse.urlparse(node.url_original)
        if p.netloc and not self.check_node_url_with_domain(p.netloc, node):
            return None
        return p.path.strip('/')

    def build_paths(self, nodes):
        data = {}
        for node in tgenerator(nodes):
            path = self.get_path(node)
            # ignore nodes with denied domain name and/or empty path
            if path is None:
                continue
            # check node is new or it is better match than previous
            if not path in data or self.compare_paths(node, data[path]):
                data[path] = node
        return data

    def merge_paths(self, paths, newpaths):
        for path, node in newpaths.items():
            # check node is new or it is better match than previous
            if not path in paths or self.compare_paths(node, paths[path]):
                paths[path] = node

    def search_selected(self, request, data):
        """Search selected node (indexed search in paths)."""
        nodes, paths, path = (data['nodes'], data['paths'],
                              request.path.strip('/').split('/'),)

        # check existance of path starting from current path down to its first
        # ancestor: on "/a/b/c/" page look for "a/b/c" or "a/b" or "a" in paths
        for pkey in ('/'.join(path[:-i or None]) for i in range(0, len(path))):
            selected = paths.get(pkey, None)
            if selected:
                # save unmodified chain up to root
                chain, item = [selected], selected
                while item.parent:
                    item = item.parent
                    chain.insert(0, item)

                # check selected for existance in morphed by
                # per_request modifiers nodes list (auth visibility, ect.)
                if not chain[0] in nodes:
                    continue

                # mark node as selected and return
                selected.selected = True

                return selected, chain
        return None, None

    # Common methods
    # --------------
    def add_nodes_to_request(self, request):
        """prepare request for menus processing"""
        if not hasattr(request, 'nodes'):
            metadata = import_path(msettings.META_DATA)
            request.nodes = metadata()

    def prepare_menus_settings(self):
        """Prepare menus settings and check validity"""

        # get menu settings for check
        MENUS = msettings.MENUS
        DEFAULT_SCHEME = msettings.DEFAULT_SCHEME

        # check MENUS
        # todo: may be someway disable menus if improperly configured
        if not isinstance(MENUS, dict) or not 'default' in MENUS:
            raise ImproperlyConfigured('Menus "MENUS" setting value'
                                       ' is empty/incorrect or not contains'
                                       ' "default" key.')

        validvalue = lambda val, chk: (set(val).__len__() == val.__len__()
                                       and all([v in chk for v in val]))

        errors = {}
        for name, value in MENUS.items():
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

            # update conf value (also with defaults)
            value.update({
                'MODIFIERS': modifiers,
                'NAME': name,
                'CACHE_TIMEOUT': value.get('CACHE_TIMEOUT',
                                           DEFAULT_SCHEME['CACHE_TIMEOUT']),
                'SELECTED': False,
            })

        if errors:
            raise ImproperlyConfigured('\n'.join(errors.values()))
