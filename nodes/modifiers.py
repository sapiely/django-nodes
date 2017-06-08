from base import Modifier, DEFAULT, ONCE, PER_REQUEST, POST_SELECT


__all__ = ('NavigationExtender', 'LoginRequired', 'Jump',
           'Namespace', 'Level', 'Root', 'CutLevels',
           'PositionalFlagsMarker', 'MetaDataProcessor',)


class Namespace(Modifier):
    """
    Fetch nodes by namespace.
    Modifier works like hard filter, filters any nodes by namespace,
    without structure integrity saving. If parent nodes in another namespace,
    Node.parent property sets to None, so current node becames new root node.
    If children contains nodes from other namespace, they will be removed.
    Example:
    n1:namespace1                               n1:namespace1
        n1.1:namespace1                 ==>         n1.1:namespace1
        n1.2:namespace2                         n1.2.1:namespace1
            n1.2.1:namespace1                       n1.2.1.1:namespace1
                n1.2.1.1:namespace1
                n1.2.1.2:namespace2
    """
    modify_event = DEFAULT

    def modify(self, request, data, meta, **kwargs):
        # main condition
        namespace = kwargs.get('namespace', None)
        if not namespace:
            return

        nodes, modified = [], False
        for node in data['nodes']:
            if node.namespace == namespace:
                nodes.append(node)
                if node.parent and node.parent.namespace != namespace:
                    node.parent, modified = None, True
                if node.children:
                    node.children = [c for c in node.children
                                     if c.namespace == namespace]

        meta.update(**{'modified_ancestors': modified,
                       'modified_descendants': modified,
                       'modified_structure': modified,})
        data['nodes'] = nodes


class Root(Modifier):
    """
    Get branch with the "root_id" (data.reverse_id) root node.
    Modifier waits "root_id" kwargs key - the id of the future root node.
    """
    modify_event = DEFAULT

    def modify(self, request, data, meta, **kwargs):
        # main condition
        root_id = kwargs.get('root_id', None)
        if not root_id:
            return

        nodes, modified = [], False
        for node in data['nodes']:
            if node.data.get('reverse_id', None) == root_id:
                # unparent and get slice with descendant length
                node.parent, modified = None, bool(node.parent)
                index = data['nodes'].index(node)
                nodes = data['nodes'][
                    index:1+index+self.get_descendants_length(node)
                ]
                break

        meta['modified_ancestors'] = modified
        data['nodes'] = nodes


class Level(Modifier):
    """
    Marks all nodes levels + save original level values (once).
    This modifier should be set after any other modifiers, but before
    CutLevels modifier, because it use levels values to limit nodes selection.

    If any modifier breaks integrity of levels values, it should set meta's
    "modified_structure" key to True (Namespace modifier do that),
    and it is means that levels values are not consistent until Level modifier
    next call.

    Note that parent/children values integrity must be guaranteed
    by any modifier.

    Note: Level adds "level" and "level_original" attributes to any node.
    """
    modify_event = ONCE | DEFAULT

    def modify(self, request, data, meta, **kwargs):
        # a bit of optimizations
        if (DEFAULT == meta['modify_event'] and not meta['modified_ancestors']):
            return

        for node in data['nodes']:
            if not node.parent:
                node.level = 0
                self.mark_levels(node)

        # save original level in data (once)
        if ONCE == meta['modify_event']:
            for n in data['nodes']:
                n.level_original = n.level

    def mark_levels(self, node):
        for child in node.children:
            child.level = node.level + 1
            self.mark_levels(child)


class Jump(Modifier):
    """Clone child url to parent if parent is marked as "jump", recursive."""
    modify_event = ONCE | PER_REQUEST

    def modify(self, request, data, meta, **kwargs):
        # a bit of optimizations
        if PER_REQUEST == meta['modify_event'] and not meta['modified_descendants']:
            return

        nodes_chain = []
        for node in data['nodes']:
            if node.children and node.data.get('jump', False):
                nodes_chain.append(node)
            elif nodes_chain:
                nodes_chain.append(node)
                self.clone_link(nodes_chain)
                nodes_chain = []

        if nodes_chain:
            self.clone_link(nodes_chain)
            nodes_chain = []

    def clone_link(self, nodes):
        for node in nodes[:-1]:
            node.url = nodes[-1].url


class LoginRequired(Modifier):
    """Remove nodes that are login required or require a group."""
    modify_event = PER_REQUEST

    def modify(self, request, data, meta, **kwargs):
        is_auth, removed_branch_length = request.user.is_authenticated(), 0
        # main condition: if user is authenticated, allow all nodes
        if is_auth:
            return

        nodes = []
        for node in data['nodes']:
            if removed_branch_length:
                removed_branch_length -= 1
                continue

            if not (is_auth if node.data.get('auth_required', False) else True):
                removed_branch_length = self.get_descendants_length(node)
                node.parent and node.parent.children.remove(node)
            else:
                nodes.append(node)

        meta['modified_descendants'] = len(nodes) != len(data['nodes'])
        data['nodes'] = nodes


class NavigationExtender(Modifier):
    """Extends menu item with another menu"""
    modify_event = ONCE

    def modify(self, request, data, meta, **kwargs):
        extenders, resort = [], False
        # rearrange the parent relations
        nodes = data['nodes']
        for node in nodes:
            currexts = node.data.get("navigation_extenders", None)
            if not currexts:
                continue
            for currext in currexts:
                if currext in extenders:
                    continue
                extenders.append(currext)
                for n in nodes:
                    # if root node has navigation extenders
                    if n.namespace == currext and not n.parent:
                        n.parent, resort = node, True
                        node.children.append(n)

        # reindex nodes if required
        if resort:
            nodes = self.format_nodes(nodes, linear=True)

        data['nodes'] = nodes


class MetaDataProcessor(Modifier):
    modify_event = POST_SELECT

    def modify(self, request, data, meta, **kwargs):
        selected = data['selected']
        chain = self._get_full_chain(data['nodes'], selected)

        metadata = request.nodes
        metadata.selected = selected
        if chain:
            metadata.keywords = getattr(metadata, 'keywords', [])
            metadata.description = getattr(metadata, 'description', [])

            # save metadata to reauest
            metadata.chain = [{'name': n.title, 'link': n.url, 'data': n.data,}
                              for n in chain] + metadata.chain
            metadata.title = [n.data.get('meta_title', u'') or n.title
                              for n in chain] + metadata.title
            metadata.keywords = [chain[-1].data.get('meta_keywords', u'')] + metadata.keywords
            metadata.description = [chain[-1].data.get('meta_description', u'')] + metadata.description
        if selected and not (chain and selected == chain[-1]):
            # set selected meta_title to title tag anyway
            metadata.title.append(selected.data.get('meta_title', u'') or selected.title)

    def _get_full_chain(self, nodes, selected):
        """get all chain elements from nodes list"""
        ancestors = []
        if selected and not selected.parent:
            if selected.data.get('visible_in_chain', True):
                ancestors.append(selected)
        elif selected:
            n = selected
            while n:
                if n.data.get('visible_in_chain', True):
                    ancestors.append(n)
                n = n.parent
        ancestors.reverse()
        return ancestors


class PositionalFlagsMarker(Modifier):
    """
    Note: Marker adds "sibling", "ancestor", "descendant", "selected"
        and "leaf" attributes to any node.
    """
    modify_event = ONCE | POST_SELECT

    def modify(self, request, data, meta, **kwargs):
        """
        On ONCE just add required attributes.
        On POST_SELECT check is selected exists, if no - just mark leaf nodes
        else mark siblings, ancestors, descendants and leaf.
        """

        if (ONCE == meta['modify_event']):
            for node in data['nodes']:
                node.sibling = node.leaf = False
                node.ancestor = node.descendant = False
            return
        elif not data['selected']:
            for node in data['nodes']:
                node.leaf = not node.children
            return

        selected, root_nodes = None, []
        for node in data['nodes']:
            node.leaf = not node.children
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


class CutLevels(Modifier):
    """
    Filters nodes by level value and/or visible value.
    Depends on Level and PositionalFlagsMarker
    """
    modify_event = DEFAULT

    def modify(self, request, data, meta, **kwargs):
        """
        Cut nodes by levels away from menus, also check visibility.
        Modifier waits "cut_levels" kwargs key, which contains all required
        values: (from_level, to_level, extra_inactive, extra_active,
                 show_invisible, show_inactive_branch)
        """

        cut_levels = kwargs.get('cut_levels', None)
        if (not cut_levels or not isinstance(cut_levels, dict)
            or not len(cut_levels) == 6 or not data['nodes']):
            return

        (from_level, to_level, extra_inactive, extra_active,
         show_invisible, show_inactive_branch) = map(cut_levels.get, [
            'from_level', 'to_level', 'extra_inactive', 'extra_active',
            'show_invisible', 'show_inactive_branch',
        ])

        # get level values related to current state
        from_level, to_level, extra_inactive, extra_active = self.parse_params(
            request, data, from_level, to_level, extra_inactive, extra_active
        )

        # default values
        nodes, selected, final = data['nodes'], data['selected'], []
        removed, in_branch = {}, False
        # check: show only active branch - ignore nodes on from_level
        # from inactive branches (not sel-sib-desc or with ancestor parent)
        only_active_branch = (not show_inactive_branch
                              and nodes[0].level < from_level)

        # main loop
        for node in nodes:
            # ignore nodes, which already is removed
            if node.id in removed:
                continue

            # check only active branch if some conditions (see above)
            # (node has parent value anyway, if only_active_branch is True)
            if only_active_branch:
                # check node is in selected branch: if node is sel-sib-desc
                # or if parent is ancestor (parent.ancestor is True)
                if not in_branch and node.level == from_level:
                    in_branch = (node.descendant or node.parent.ancestor
                                                 or node.sibling
                                                 or node.selected)
                # break if node lower then from_level (selected branch
                # retrieved completely at this moment)
                elif in_branch and node.level < from_level:
                    break
                # just ignore left side relative to selected branch
                if not in_branch:
                    continue
            # ignore nodes lower then from_level
            elif node.level < from_level:
                continue

            # remove nodes that are too deep or invisible if not show_invisible
            if (node.level > to_level) or (not show_invisible and not node.visible):
                self.remove(node, removed)
                continue

            # cut inactive nodes to extra_inactive (not any of sel-sib-desc)
            # or cut active nodes (selected node's descendants) to extra_active
            if node.children:
                if not (node.selected or node.ancestor or node.descendant):
                    self.cut_after(node, extra_inactive, removed)
                elif node.selected:
                    self.cut_after(node, extra_active, removed)

            # turn nodes that are on from_level into root nodes (unparent)
            # also, if root node is descendant, then selected node lower then
            # from_level, but root still in active branch, so cut extra_active
            if node.level == from_level:
                node.parent = None
                if node.descendant:
                    self.cut_after(node, extra_active, removed)

            final.append(node)

        # update meta information and nodes data
        if len(final) != len(data['nodes']):
            meta.update(modified_ancestors=from_level > 0,
                        modified_descendants=True)
        data['nodes'] = final

    def cut_after(self, node, level, removed):
        """Cut nodes from tree after specified level."""
        if not node.children:
            return
        elif level <= node.level:
            for n in node.children:
                removed[n.id] = None
                n.children and self.cut_after(n, 0, removed)
            node.children = []
        else:
            for n in node.children:
                n.children and self.cut_after(n, level-1, removed)

    def remove(self, node, removed):
        """Remove node from tree."""
        removed[node.id] = None
        if node.parent and node in node.parent.children:
            node.parent.children.remove(node)
        if node.children:
            self.cut_after(node, 0, removed)

    def parse_params(self, request, data, *params):
        """
        Process params with {so}, {s}, {ro}, {r} patterns, if defined.
        Allowed values:
            (0, 10, 10, 10,)                - direct integer values,
            ({s}, {s}+10, {ro}+1, {s}+10,)  - expressions (see below)

        Values should contains only digits, [+-] signs and {so}, {s}, {ro}, {r}
        patterns, which are selected, selected-original, root and root-original
        level values respectively. If value is invalid - it will be set to 0.
        """

        check = lambda x: isinstance(x, int) and x >= 0
        nodes, selected = data['nodes'], data['selected']
        root = nodes and nodes[0] or None

        # get selected-original, selected, root-original, root
        so, s = (selected.level_original, selected.level) if selected else (0, 0,)
        ro, r = (root.level_original, root.level,) if root else (0, 0,)

        # params as list for direct assignation (*args are tuple)
        params = list(params)

        # process each params
        for i, param in enumerate(params):
            if check(param):
                continue
            param = (str(param) or '0') if param else '0'
            param = param.format(so=so, s=s, ro=ro, r=r)
            value = param.replace('+', '').replace('-', '').isdigit()
            value = eval(param) if value else 0
            params[i] = value if value > 0 else 0

        return params
