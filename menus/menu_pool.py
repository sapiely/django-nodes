from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils.translation import get_language
from .base import NamespaceAllreadyRegistered
from .utils import meta_to_request, cache_key_generator, setting_importable
import copy, urlparse

# get settings
CHECK_URL_DOMAIN    = setting_importable('MENUS_CHECK_URL_DOMAIN', 
                                         lambda domain, node: False)
MODIFIERS_REG       = setting_importable('MENUS_MODIFIERS_REG', None)
PATH_COMPARE        = setting_importable('MENUS_PATH_COMPARE', None)
CACHE_DURATION      = getattr(settings, 'MENUS_CACHE_DURATION', 600)
MENUS_APPS          = getattr(settings, 'MENUS_APPS', None)


class MenuPool(object):
    def __init__(self):
        self.menus = {}
        self.modifiers = []
        self.discovered = False
        self.cache_keys = set()

    def discover_menus(self):
        if self.discovered: return
        for app in MENUS_APPS:
            __import__(app, {}, {}, ['menu'])
        self.discovered = True
        # register modifiers
        from modifiers import register
        callback = MODIFIERS_REG or register
        callback()

    def clear(self, site_id=None, language=None):
        """clear cache data"""
        def relevance_test(keylang, keysite):
            sok = not site_id
            lok = not language
            if site_id and (site_id == keysite or site_id == int(keysite)):
                sok = True
            if language and language == keylang:
                lok = True
            return lok and sok
        to_be_deleted = []
        for key in self.cache_keys:
            keylang, keysite = cache_key_generator(key=key)
            if relevance_test(keylang, keysite):
                to_be_deleted.append(key)
        cache.delete_many(to_be_deleted)
        self.cache_keys.difference_update(to_be_deleted)

    def register_menu(self, menu):
        from base import Menu
        assert issubclass(menu, Menu)
        if menu.__name__ in self.menus.keys():
            raise NamespaceAllreadyRegistered, '[%s] a menu with this name is already ' \
                                               'registered' % menu.__name__
        self.menus[menu.__name__] = menu()

    def register_modifier(self, modifier_class):
        from base import Modifier
        assert issubclass(modifier_class, Modifier)
        if not modifier_class in self.modifiers:
            self.modifiers.append(modifier_class)

    def unregister_modifier(self, modifier_class):
        from base import Modifier
        assert issubclass(modifier_class, Modifier)
        if modifier_class in self.modifiers:
            self.modifiers.remove(modifier_class)

    def clear_modifiers(self):
        self.modifiers = []

    def get_nodes(self, request, namespace=None, root_id=None, 
                                  site_id=None, init_only=False):
        # prepare request
        meta_to_request(request)

        # cache marked menu while request
        if hasattr(request.meta, '_nodes'):
            nodes = request.meta._nodes
        else:
            # also cachable, but between requests
            self.discover_menus()

            # cached nodes list selection
            cache_key = cache_key_generator(get_language(), 
                                             site_id or Site.objects.get_current().pk, request)
            self.cache_keys.add(cache_key)
            nodes, paths = cache.get(cache_key, (None,)*2)
            if not nodes:
                nodes = self._build_nodes(request)
                nodes = self.apply_modifiers(nodes, request, modify_rule='once')
                paths = self._build_paths(nodes)
                cache.set(cache_key, [nodes, paths], CACHE_DURATION)

            nodes = self.apply_modifiers(nodes, request, modify_rule='per_request')
            selected = self._mark_selected(request, paths)
            self._mark_anc_des_sib_flags(nodes)
            self._storage_trigger(request, nodes, selected)
            request.meta._nodes = nodes

        if init_only: return
        nodes, meta = copy.deepcopy(nodes), None
        if root_id:
            nodes, meta = self._nodes_in_root(nodes, root_id), {'modified_ancestors': True}
        return self.apply_modifiers(nodes, request, namespace, root_id, post_cut=False, meta=meta)

    def apply_modifiers(self, nodes, request, namespace=None, root_id=None, post_cut=False, 
                                               meta=None, modify_rule='every_time'):
        meta, meta['modify_rule'] = meta or {}, modify_rule
        for cls in self.modifiers:
            if not modify_rule in cls.modify_rule: continue
            nodes = cls().modify(request, nodes, namespace, root_id, post_cut, meta)
        return nodes

    def get_nodes_by_attribute(self, nodes, name, value):
        found = []
        for node in nodes:
            node.attr.get(name, None) == value and found.append(node)
        return found

    def _nodes_in_root(self, nodes, root_id):
        """get nodes in node with reverse_id == root_id"""
        new_nodes = []
        id_nodes = self.get_nodes_by_attribute(nodes, 'reverse_id', root_id)
        if id_nodes:
            new_nodes = self._nodes_after_node(id_nodes[0], [], unparent=True)
        return new_nodes

    def _nodes_after_node(self, node, result, unparent=False):
        if not node.children:
            return result
        for n in node.children:
            result.append(n)
            if unparent:
                n.parent = None
            if n.children:
                result = self._nodes_after_node(n, result)
        return result

    def _build_nodes(self, request):
        """build full nodes array (linear) with parent links"""
        final_nodes, ignored_nodes = {'ids':{}, 'nodes':[]}, {}

        # sort node by index attr desc
        menus = self.menus.values()
        menus = sorted(menus, cmp=lambda x,y: cmp(x.index, y.index))
        # fetch all nodes from all menus
        for menu in menus:
            nodes, last = menu.get_nodes(request), None
            for node in nodes:
                # set namespace (menu class name)
                node.namespace = node.namespace or menu.namespace
                final_nodes['ids'][node.namespace] = final_nodes['ids'].get(node.namespace, [])
                ignored_nodes[node.namespace] = ignored_nodes.get(node.namespace, [])

                # ignore nodes with dublicated ids
                if node.id in final_nodes['ids'][node.namespace]:
                    continue
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
                    # search parent directrly
                    if not found:
                        for n in nodes:
                            if n.namespace == node.namespace and n.id == node.parent_id:
                                node.parent, found = n, True
                    # if parent is found - append node to "brothers"
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

        # reindex ids in nodes array
        final_nodes, i = final_nodes['nodes'], 1
        for node in final_nodes:
            node.id, node.parent_id, i = i, node.parent and node.parent.id, i+1
            node.sibling, node.ancestor, node.descendant, node.selected = (False,)*4
        return final_nodes

    # maximize selection speed with paths dict
    def _get_path(self, node):
        p = urlparse.urlparse(node.url_original)
        if p.netloc and not CHECK_URL_DOMAIN(p.netloc, node):
            return None, False
        return p.path.strip('/').split('/'), not bool(p.params or p.query or p.fragment)

    def _better_path(self, path, clean, node, ppath, pclean, pnode):
        if PATH_COMPARE and callable(PATH_COMPARE):
            return PATH_COMPARE(path, clean, node, ppath, pclean, pnode, menupool=self)

        return len(path) < len(ppath) or (len(path) == len(ppath) and clean >= pclean)

    def _build_paths(self, nodes):
        data = {}
        for node in nodes:
            path, clean = self._get_path(node)
            # ignore nodes with denied domain name
            if not path: continue

            for item in ['/'.join(path[:i]) for i in range(1, len(path)+1)]:
                if data.has_key(item):
                    # check this node better match than previous
                    ppath, pclean = self._get_path(data[item])
                    if self._better_path(path, clean, node, ppath, pclean, data[item]):
                        data[item] = node
                else:
                    # link path with node
                    data[item] = node
        return data

    def _mark_selected(self, request, paths):
        """mark current node as selected"""
        path = request.path.strip('/').split('/')
        for pkey in ['/'.join(path[:-i or None]) for i in range(0, len(path))]:
            selected = paths.get(pkey, None)
            if selected:
                selected.selected = True
                return selected

    def _mark_anc_des_sib_flags(self, nodes):
        """
        searches the current selected node and marks them.
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
        return

    def _mark_descendants(self, nodes):
        for node in nodes:
            node.descendant = True
            node.children and self._mark_descendants(node.children)

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

    def _get_selected(self, nodes):
        for node in nodes:
            if node.selected: return node

    def _storage_trigger(self, request, nodes, selected):
        """request.meta data inserter trigger"""
        chain = self._get_full_chain(nodes, selected)
        request.meta.current = selected
        if chain:
            # storage meta data
            request.meta.chain = [{'name': n.title, 'link': n.url, 
                                   'attr': n.attr,} for n in chain] + request.meta.chain
            request.meta.title = [n.meta_title for n in chain] + request.meta.title
            request.meta.keywords = [chain[-1].meta_keywords] + request.meta.keywords
            request.meta.description = [chain[-1].meta_description] + request.meta.description
        if selected and not (chain and selected == chain[-1]):
            # set selected meta_title to title tag anyway
            request.meta.title.append(selected.meta_title)

menu_pool = MenuPool()