from base import Modifier

__all__ = ('NavExtender', 'LoginRequired', 'Jump', 'Namespace', 'Level',)

class Namespace(Modifier):
    """fetch nodes by namespace"""
    modify_rule = ('every_time',)

    def modify(self, request, nodes, namespace, root_id, post_cut, meta={}):
        # activate condition
        if not namespace or post_cut:
            return nodes

        data, nodes = nodes, []
        for node in data:
            if node.namespace == namespace:
                nodes.append(node)
                if node.parent and node.parent.namespace != namespace:
                    node.parent = None
                if node.children:
                    children, node.children = node.children, []
                    for c in children:
                        c.namespace == namespace and node.children.append(c)

        meta['modified_ancestors'] = meta['modified_descendants'] = True
        return nodes

class Level(Modifier):
    """marks all node levels"""
    modify_rule = ('once', 'every_time',)

    def modify(self, request, nodes, namespace, root_id, post_cut, meta={}):
        # activate condition
        if post_cut or ('every_time' == meta['modify_rule']
                        and not meta.get('modified_ancestors', False)):
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
    modify_rule = ('once', 'per_request',)

    def modify(self, request, nodes, namespace, root_id, post_cut, meta={}):
        # activate condition
        if 'per_request' == meta['modify_rule'] and not meta.get('modified_descendants', False):
            return nodes

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
    modify_rule = ('per_request',)

    def modify(self, request, nodes, namespace, root_id, post_cut, meta={}):
        # activate condition
        is_auth, is_none = request.user.is_authenticated(), 0
        if is_auth: return nodes

        for node in nodes:
            good = is_auth if node.attr.get('auth_required', False) else True
            if not good:
                self.remove_branch(node, nodes)
                # shift index for corrent cycling
                nodes.insert(0, None)
                is_none += 1

        # remove None items from nodes
        if is_none:
            nodes = nodes[is_none:]
            meta['modified_descendants'] = True

        return nodes

class NavExtender(Modifier):
    """Extends menu item with another menu"""
    modify_rule = ('once',)

    def modify(self, request, nodes, namespace, root_id, post_cut, meta={}):
        exts, resort = [], False
        # rearrange the parent relations
        for node in nodes:
            extenders = node.attr.get("navigation_extenders", None)
            if extenders:
                for ext in extenders:
                    ext in exts or exts.append(ext)
                    for n in nodes:
                        # if root node has nav extenders
                        target = []
                        if n.namespace == ext and not n.parent_id:
                            n.parent, n.parent_id, resort = node, node.id, True
                            node.children.append(n)

        # reindex nodes if required
        if resort:
            nodes = self.resort_nodes(nodes)

        return nodes