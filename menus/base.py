from django.core.exceptions import ValidationError
from django.utils.translation import get_language
from django.utils.encoding import smart_str

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
    modify_rule = 'every_time'

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
    attr                = None

    visible             = True
    visible_chain       = True

    parent              = None # do not touch
    namespace           = None

    meta_title          = None
    meta_keywords       = None
    meta_description    = None

    def __init__(self, title, url, id, parent_id=None, attr=None,
                  visible=True, visible_chain=True,
                   meta_title='', meta_keywords='', meta_description=''):
        self.children           = [] # do not touch
        self.title              = title
        self.url                = url
        self.id                 = id
        self.parent_id          = parent_id
        self.visible            = visible
        self.visible_chain      = visible_chain
        self.meta_title         = meta_title
        self.meta_keywords      = meta_keywords
        self.meta_description   = meta_description
        self.attr               = attr or {}

    def __repr__(self):
        return "<Navigation Node: %s>" % smart_str(self.title)

    def get_descendants(self):
        nodes = []
        for node in self.children:
            nodes.append(node)
            nodes += node.get_descendants()
        return nodes