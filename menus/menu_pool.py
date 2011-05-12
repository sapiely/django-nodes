from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.utils.translation import get_language
from toolbox import NamespaceAllreadyRegistered, meta_to_request, cache_key_tool
import copy

class MenuPool(object):
    def __init__(self):
        self.menus = {}
        self.modifiers = []
        self.discovered = False
        self.cache_keys = set()

    def discover_menus(self):
        if self.discovered: return
        for app in settings.MENUS_APPS:
            __import__(app, {}, {}, ['menu'])
        from modifiers import register
        register()
        self.discovered = True

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
            keylang, keysite = cache_key_tool(key=key)
            if relevance_test(keylang, keysite):
                to_be_deleted.append(key)
        cache.delete_many(to_be_deleted)
        self.cache_keys.difference_update(to_be_deleted)

    def register_menu(self, menu):
        from base import Menu
        assert issubclass(menu, Menu)
        if menu.__name__ in self.menus.keys():
            raise NamespaceAllreadyRegistered, "[%s] a menu with this name is already registered" % menu.__name__
        self.menus[menu.__name__] = menu()

    def register_modifier(self, modifier_class):
        from base import Modifier
        assert issubclass(modifier_class, Modifier)
        if not modifier_class in self.modifiers:
            self.modifiers.append(modifier_class)

    def get_nodes(self, request, namespace=None, root_id=None, site_id=None, breadcrumb=False):

        # prepare request
        meta_to_request(request)
        
        # cache marked menu while request
        if hasattr(request.meta, '_nodes'):
            nodes = request.meta._nodes
        else:
            # also cachable, but between requests
            # remark (second _mark_selected) required after some modifiers (LoginRequired)
            self.discover_menus()
            site_id = site_id if site_id else Site.objects.get_current().pk
            cache_key = cache_key_tool(get_language(), site_id, request)
            nodes = self._build_nodes(request, cache_key)
            nodes = copy.deepcopy(nodes)
            nodes = self._mark_selected(request, nodes)
            nodes = self.apply_modifiers(nodes, request, modify_once=True)
            nodes = self._mark_selected(request, nodes)
            nodes = self._mark_anc_des_sib_flags(nodes)
            request.meta._nodes = nodes
            self._storage_trigger(request, nodes)

        nodes = copy.deepcopy(nodes)
        nodes = self.apply_modifiers(nodes, request, namespace, root_id, post_cut=False, breadcrumb=breadcrumb)

        return nodes

    def apply_modifiers(self, nodes, request, namespace=None, root_id=None, post_cut=False, breadcrumb=False, modify_once=False):
        for cls in self.modifiers:
            if bool(modify_once) != bool(cls.modify_once): continue
            nodes = cls().modify(request, nodes, namespace, root_id, post_cut, breadcrumb)
        return nodes

    def get_menus_by_attribute(self, name, value):
        self.discover_menus()
        found = []
        for menu in self.menus.items():
            if hasattr(menu[1], name) and getattr(menu[1], name, None) == value:
                found.append((menu[0], menu[1].name))
        return found

    def get_nodes_by_attribute(self, nodes, name, value):
        found = []
        for node in nodes:
            if node.attr.get(name, None) == value:
                found.append(node)
        return found

    def _build_nodes(self, request, cache_key):
        """
        build full nodes array (linear) with parent links
        cachable operation
        call from menu_pool.get_nodes
        """
        self.cache_keys.add(cache_key)
        cached_nodes = cache.get(cache_key, None)
        if cached_nodes: return cached_nodes

        final_nodes = []
        for ns in self.menus:
            try:
                nodes = self.menus[ns].get_nodes(request)
            except:
                raise
            last = None
            for node in nodes:
                if not node.namespace:
                    node.namespace = ns
                if node.parent_id:
                    found = False
                    if last:
                        n = last
                        while n:
                            if n.namespace == node.namespace and n.id == node.parent_id:
                                node.parent = n
                                found = True
                                n = None
                            elif n.parent:
                                n = n.parent
                            else:
                                n = None
                    if not found:
                        for n in nodes:
                            if n.namespace == node.namespace and n.id == node.parent_id:
                                node.parent = n
                                found = True
                    if found:
                        node.parent.children.append(node)
                    else:
                        continue
                final_nodes.append(node)
                last = node
        cache.set(cache_key, final_nodes, settings.MENUS_CACHE_DURATION)

        return final_nodes

    def _mark_selected(self, request, nodes):
        """mark current node as selected"""
        sel = None
        for node in nodes:
            node.sibling = False
            node.ancestor = False
            node.descendant = False
            node.selected = False

            if node.url == request.path[:len(node.url)]:
                if sel:
                    if len(node.url) >= len(sel.url):
                        sel = node
                else:
                    sel = node
            else:
                node.selected = False
        if sel:
            sel.selected = True
        return nodes

    def _mark_anc_des_sib_flags(self, nodes):
        """
        searches the current selected node and marks them.
        current_node: selected = True
        siblings: sibling = True
        descendants: descendant = True
        ancestors: ancestor = True
        (become from modifier)
        """
        selected = None
        root_nodes = []
        for node in nodes:
            if not hasattr(node, "descendant"):
                node.descendant = False
            if not hasattr(node, "ancestor"):
                node.ancestor = False
            if not node.parent:
                if selected and not selected.parent:
                    node.sibling = True
                root_nodes.append(node)
            if node.selected:
                if node.parent:
                    n = node
                    while n.parent:
                        n = n.parent
                        n.ancestor = True
                    for sibling in node.parent.children:
                        if not sibling.selected:
                            sibling.sibling = True
                else:
                    for n in root_nodes:
                        if not n.selected:
                            n.sibling = True
                if node.children:
                    self._mark_descendants(node.children)
                selected = node
            if node.children:
                node.is_leaf_node = False
            else:
                node.is_leaf_node = True
        return nodes

    def _mark_descendants(self, nodes):
        for node in nodes:
            node.descendant = True
            self._mark_descendants(node.children)

    def _get_selected(self, nodes):
        selected = None
        for node in nodes:
            if node.selected:
                selected = node
        return selected
        
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

    def _storage_trigger(self, request, nodes):
        """request.meta data inserter trigger"""
        nodes = self.get_nodes(request, breadcrumb=True)
        selected = self._get_selected(nodes)
        chain = self._get_full_chain(nodes, selected)
        
        request.meta.current = selected
        if chain:
            # storage meta data
            request.meta.chain = [{'name':n.title, 'link':n.url, 'attr':n.attr} for n in chain] + request.meta.chain
            request.meta.title = [n.meta_title for n in chain] + request.meta.title
            request.meta.keywords = [chain[-1].meta_keywords] + request.meta.keywords
            request.meta.description = [chain[-1].meta_description] + request.meta.description
        if selected and not (chain and selected == chain[-1]):
            # set selected meta_title to title tag anyway
            request.meta.title.append(selected.meta_title)
        
menu_pool = MenuPool()