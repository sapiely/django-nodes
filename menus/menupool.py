from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils.translation import get_language
from .utils import meta_to_request
from . import settings as msettings
import copy, urlparse, re

class MenuPool(object):

    # methods that are expected to extend if required:
    #   router - menuconf router by request
    #   check_node_url_with_domain - check urls with domain specified
    #   compare_path - compare two paths by length, get/hash existance, ect
    #   request_meta_processor - how to insert sel-anc nodes to meta container
    #   cache_key - cahce name generator for confname

    registry = None

    def __init__(self, registry):
        self.registry = registry
        self._cache_keys = set()
        self._modifiers = {}

    def router(self, request):
        for route, conf in msettings.MENU_ROUTES:
            if re.match(route, request.path):
                return conf

        return 'default'

    def menuconf(self, request, name=None):
        """get menuconf value, call router if required (once)"""

        # update request with meta
        meta_to_request(request)

        # call router once per request
        if not hasattr(request.meta, '_menuconf'):
            request.meta._menucurr = self.router(request)
            request.meta._menuconf = {}

        # get menuconf and cache it
        name = name or request.meta._menucurr
        conf = request.meta._menuconf.get(name, None)
        if not conf:
            conf = msettings.MENU_CONF.get(name, None)
            if conf is None:
                raise ValueError('Menus menuconf invalid name (%s).' % name)

            conf['CURRENT'] = name == request.meta._menucurr
            request.meta._menuconf[name] = conf

        return conf

    def cache_key(self, request=None, menuconf=None,
                         lang=None, site_id=None, key=None):
        """
        generate cache_key by lang and site_id or
        return lang and site_id from key value
        """
        if key:
            return key.split('_', 3)[1:4]

        lang = lang or get_language()
        site_id = site_id or Site.objects.get_current().pk
        return 'menus_%s_%s_%s_cache' % (menuconf, lang, site_id)

    def cache_clear(self, menuconf=None, site_id=None, language=None):
        """clear cache data [by site_id and language]"""
        def relevance_test(keyconf, keylang, keysite):
            sok, lok, cok = not site_id, not language, not menuconf
            if site_id and (site_id == int(keysite)):
                sok = True
            if language and language == keylang:
                lok = True
            if menuconf and menuconf == keyconf:
                cok = True
            return lok and sok and cok

        to_be_deleted = []
        for key in self._cache_keys:
            keyconf, keylang, keysite = self.cache_key(key=key)
            if relevance_test(keyconf, keylang, keysite):
                to_be_deleted.append(key)
        cache.delete_many(to_be_deleted)
        self._cache_keys.difference_update(to_be_deleted)

    def get_nodes(self, menuconf, request, namespace=None,
                                  root_id=None, init_only=False):
        """generate menu nodes list by menu confname and some filters"""

        # get menu configuration data (dict value expected as valid)
        # also if menuconf is dict -> request is already meta-processed
        menuconf = menuconf if menuconf and isinstance(menuconf, dict) \
                            else self.menuconf(request, name=menuconf)

        # temp requested menuconf nodes in request object
        nodes = getattr(request.meta, '_menus', {}).get(menuconf['NAME'], None)
        if nodes is None:
            request.meta._menus = getattr(request.meta, '_menus', {})

            # longtime between-request cached code
            cache_key = self.cache_key(request=request, menuconf=menuconf['NAME'])
            self._cache_keys.add(cache_key)
            nodes, paths = cache.get(cache_key, (None,)*2)
            if not nodes:
                nodes = self._build_nodes(request, menuconf['MENUS'])
                nodes = self.apply_modifiers(menuconf, nodes, request, modify_rule='once')
                paths = self._build_paths(nodes)
                cache.set(cache_key, (nodes, paths,), menuconf['CACHE_TIMEOUT'])

            # per-request cached code
            nodes = self.apply_modifiers(menuconf, nodes, request, modify_rule='per_request')

            # current-selected node related code
            # check does menu is routed (CURRENT) or requested directly
            # only CURRENT menu nodes mark as selected
            # todo: may be add CHECK_SELECTION param to conf?
            if menuconf['CURRENT']:
                selected = self._mark_selected(request, paths, nodes)
                self._mark_anc_des_sib_flags(nodes) # also leaf check here
                self.request_meta_processor(request, nodes, selected)
            else:
                self._mark_leaf_flags(nodes)

            request.meta._menus[menuconf['NAME']] = nodes

        if init_only: return

        # clone nodes and process with root_id and every-time apply_modifiers
        nodes, meta = copy.deepcopy(nodes), None
        if root_id:
            nodes, meta = self._nodes_in_node(nodes, root_id), {'modified_ancestors': True,}
        return self.apply_modifiers(menuconf, nodes, request, namespace=namespace,
                                               root_id=root_id, post_cut=False, meta=meta)

    def apply_modifiers(self, menuconf, nodes, request, namespace=None, root_id=None,
                               post_cut=False, meta=None, modify_rule='every_time'):
        """process nodes with modifiers, related to menu confname"""

        # get menu configuration data (dict value expected as valid)
        menuconf = menuconf if menuconf and isinstance(menuconf, dict) \
                            else self.menuconf(request, name=menuconf)

        # cache modifiers list by menuconf name
        modifiers = self._modifiers.get(menuconf['NAME'], None)
        if not modifiers:
            modifiers = self.registry.modifiers
            modifiers = [modifiers[mod] for mod in menuconf['MODIFIERS']]
            self._modifiers[menuconf['NAME']] = modifiers

        # process
        meta, meta['modify_rule'] = meta or {}, modify_rule
        for mod in modifiers:
            if not modify_rule in mod.modify_rule: continue
            nodes = mod.modify(request, nodes, namespace, root_id, post_cut, meta)
        return nodes

    def get_nodes_by_attribute(self, nodes, name, value):
        found = []
        for node in nodes:
            node.attr.get(name, None) == value and found.append(node)
        return found

    # raw menus nodes list generator
    def _build_nodes(self, request, menus):
        """build raw full nodes array (linear) with parent links"""
        final_nodes, ignored_nodes = {'ids':{}, 'nodes':[],}, {}

        # get menus from registry and sort by index attr desc
        menus = [self.registry.menus[m] for m in menus]
        menus = sorted(menus, cmp=lambda x,y: cmp(x.index, y.index))

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
                if node.parent_id:
                    found = False
                    # ignore node if parent also ignored
                    if node.parent_id in ignored_nodes[node.namespace]:
                        ignored_nodes[node.namespace].append(node.id)
                        continue
                    # try to find parent in ancestors chain (optimization)
                    if last:
                        n = last
                        while n:
                            if n.namespace == node.namespace and n.id == node.parent_id:
                                node.parent, found, n = n, True, None
                            else:
                                n = n.parent or None
                    # search parent directrly (slowly)
                    if not found:
                        for n in nodes:
                            if n.namespace == node.namespace and n.id == node.parent_id:
                                node.parent, found = n, True
                    # if parent is found - append node to "brothers", else ignore invalid
                    if found:
                        node.parent.children.append(node)
                    else:
                        ignored_nodes[node.namespace].append(node.id)
                        continue
                # append node and it is to main list
                final_nodes['nodes'].append(node)
                final_nodes['ids'][node.namespace].append(node.id)
                # last node for search in ancestors
                last = node

        # reindex ids in nodes array, also create node attrs (sib, anc, des, sel)
        final_nodes, i = final_nodes['nodes'], 1
        for node in final_nodes:
            node.id, node.parent_id, i = i, node.parent and node.parent.id, i+1
            node.sibling, node.ancestor, node.descendant, node.selected = (False,)*4
        return final_nodes

    # branch with specified node as root
    def _nodes_in_node(self, nodes, root_id):
        """get nodes in node with reverse_id == root_id"""
        new_nodes = []
        for node in nodes:
            if node.attr.get('reverse_id', node.id) == root_id:
                new_nodes = self._nodes_after_node(node, [], unparent=True)
                break

        return new_nodes

    def _nodes_after_node(self, node, result, unparent=False):
        if not node.children:
            return result
        for n in node.children:
            result.append(n)
            if unparent:
                n.root, n.parent = n.parent, None
            if n.children:
                result = self._nodes_after_node(n, result)
        return result

    # maximize selection speed with paths dict
    def check_node_url_with_domain(self, domain, node):
        return False

    def compare_path(self, path, clean, node, ppath, pclean, pnode):
        return len(path) < len(ppath) or (len(path) == len(ppath) and clean >= pclean)

    def _get_path(self, node):
        p = urlparse.urlparse(node.url_original)
        if p.netloc and not self.check_node_url_with_domain(p.netloc, node):
            return None, False
        return p.path.strip('/').split('/'), not bool(p.params or p.query or p.fragment)

    def _build_paths(self, nodes):
        data = {}
        for node in nodes:
            path, clean = self._get_path(node)
            # ignore nodes with denied domain name
            if not path: continue

            for item in ['/'.join(path[:i]) for i in range(1, len(path)+1)]:
                if data.has_key(item):
                    # check this node is better match than previous
                    ppath, pclean = self._get_path(data[item])
                    if self.compare_path(path, clean, node, ppath, pclean, data[item]):
                        data[item] = node
                else:
                    # link path with node
                    data[item] = node
        return data

    def _mark_selected(self, request, paths, nodes):
        """mark current node as selected (indexed search in paths)"""

        # id dict for speedup (indexed) node search
        nodekeys = dict((n.id, None) for n in nodes)

        path = request.path.strip('/').split('/')
        for pkey in ['/'.join(path[:-i or None]) for i in range(0, len(path))]:
            selected = paths.get(pkey, None)
            if selected:
                # check selected for existance in morphed with
                # per_request modifiers nodes list (auth visibility, ect)
                if not selected.id in nodekeys:
                    continue

                selected.selected = True
                return selected

    # leaf and sel-anc-des-sib flags markers
    def _mark_leaf_flags(self, nodes):
        """mark is_leaf_node (use if non routed menu)"""
        for node in nodes:
            node.is_leaf_node = not node.children

    def _mark_anc_des_sib_flags(self, nodes):
        """
        searches the current selected node and marks them
        also mark each node as leaf if it has no children
        current: selected = True
        siblings: sibling = True
        descendants: descendant = True
        ancestors: ancestor = True
        """
        selected, root_nodes = None, []
        for node in nodes:
            node.is_leaf_node = not node.children
            node.parent or root_nodes.append(node)
            if node.selected:
                selected = node
                if node.parent:
                    n = node
                    while n.parent:
                        n = n.parent
                        n.ancestor = True
                    for sibling in node.parent.children:
                        sibling.sibling = not sibling.selected
                if node.children:
                    self._mark_descendants(node.children)
        if selected and not selected.parent:
            for n in root_nodes:
                n.sibling = not n.selected
        return selected

    def _mark_descendants(self, nodes):
        for node in nodes:
            node.descendant = True
            node.children and self._mark_descendants(node.children)

    # other utils: current selector
    def _get_selected(self, nodes):
        for node in nodes:
            if node.selected: return node

    # meta processor: how to insert sel-anc nodes to meta
    def request_meta_processor(self, request, nodes, selected):
        """request.meta data processor"""
        chain = self._get_full_chain(nodes, selected)
        request.meta.current = selected
        if chain:
            # save meta data to reauest
            request.meta.chain = [{'name': n.title, 'link': n.url,
                                   'attr': n.attr,} for n in chain] + request.meta.chain
            request.meta.title = [n.meta_title or n.title for n in chain] + request.meta.title
            request.meta.keywords = [chain[-1].meta_keywords] + request.meta.keywords
            request.meta.description = [chain[-1].meta_description] + request.meta.description
        if selected and not (chain and selected == chain[-1]):
            # set selected meta_title to title tag anyway
            request.meta.title.append(selected.meta_title or selected.title)

    def _get_full_chain(self, nodes, selected):
        """get all chain elements from nodes list"""
        ancestors = []
        if selected and not selected.parent:
            if selected.visible_chain:
                ancestors.append(selected)
        elif selected:
            n = selected
            while n:
                if n.visible_chain:
                    ancestors.append(n)
                n = n.parent
        ancestors.reverse()
        return ancestors