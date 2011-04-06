from django.conf import settings
from menus.base import Modifier
from menus.menu_pool import menu_pool

class Namespace(Modifier):
    """fetch nodes by namespace"""

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if not namespace or post_cut or breadcrumb:
            return nodes
        data = []
        for node in nodes:
            if node.namespace == namespace:
                data.append(node)
                if node.parent and node.parent.namespace != namespace:
                    node.parent = None
                if node.children:
                    children, node.children = node.children, []
                    for c in children:
                        c.namespace == namespace and node.children.append(c)
        if data:
            nodes = data

        return nodes

class Level(Modifier):
    """marks all node levels"""

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if breadcrumb or post_cut:
            return nodes
        for node in nodes:
            if not node.parent:
                node.level = 0
                self.mark_levels(node)

        return nodes

    def mark_levels(self, node):
        for child in node.children:
            child.level = node.level + 1
            self.mark_levels(child)

class Jump(Modifier):
    """Clone child link to parent if parent is marked as jump"""
    modify_once = True

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        nodes_chain = []
        for node in nodes:
            if node.children and node.attr.get('jump', False):
                nodes_chain.append(node)
            elif len(nodes_chain):
                nodes_chain.append(node)
                self.clone_link(nodes_chain)
                nodes_chain = []

        if len(nodes_chain):
            self.clone_link(nodes_chain)
            nodes_chain = []

        return nodes

    def clone_link(self, nodes):
        for node in nodes[:-1]:
            node.url = nodes[-1].url

class LoginRequired(Modifier):
    """Remove nodes that are login required or require a group"""
    modify_once = True

    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut or breadcrumb:
            return nodes

        is_auth = request.user.is_authenticated()
        is_none = 0
        
        for node in nodes:
            good = is_auth if node.attr.get('auth_required', False) else True
            if not good:
                self.remove_branch(node, nodes)
                # shift index
                nodes.insert(0, None)
                is_none += 1

        # remove None items from nodes
        nodes = nodes[is_none:] if is_none else nodes

        return nodes
        
class NavExtender(Modifier):
    """Extends menu item with another menu"""
    modify_once = True
    
    def modify(self, request, nodes, namespace, root_id, post_cut, breadcrumb):
        if post_cut:
            return nodes
        exts = []
        # rearrange the parent relations
        for node in nodes:
            extenders = node.attr.get("navigation_extenders", None)
            if extenders:
                for ext in extenders:
                    if not ext in exts:
                        exts.append(ext)
                    for n in nodes:
                        # if root node has nav extenders
                        if n.namespace == ext and not n.parent_id:
                            n.parent_id = node.id
                            n.parent = node
                            node.children.append(n)

        return nodes

def register():
    menu_pool.register_modifier(NavExtender)
    menu_pool.register_modifier(LoginRequired)
    menu_pool.register_modifier(Jump)
    menu_pool.register_modifier(Namespace)
    menu_pool.register_modifier(Level)