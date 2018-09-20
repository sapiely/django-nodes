from .base import Modifier, DEFAULT, ONCE, PER_REQUEST, POST_SELECT
from .utils import tgenerator, tcutter, tfilter


__all__ = ('NavigationExtender', 'AuthVisibility', 'Jump',
           'Namespace', 'Level', 'Root', 'CutLevels',
           'PositionalMarker', 'MetaDataProcessor',)


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

        temp = {'count': 0,}  # for closure

        def checker(node):
            if node.namespace != namespace:
                temp['count'] += 1
                return False
            return True

        # filter nodes by namespace
        data['nodes'] = tfilter(data['nodes'], checker)
        temp['count'] and meta.update(modified_ancestors=True,
                                      modified_descendants=True)


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

        nodes, modified_ancestors = [], False
        for node in tgenerator(data['nodes']):
            if node.data.get('reverse_id', None) == root_id:
                node.parent, modified_ancestors = None, bool(node.parent)
                nodes = [node]
                break

        meta['modified_ancestors'] = modified_ancestors
        data['nodes'] = nodes


class Level(Modifier):
    """
    Marks all nodes levels + save original level values (once).
    Usually this modifier should be set after any other modifiers.

    If any modifier breaks integrity of levels values, it should set meta's
    "modified_ancestors" key to True (Namespace modifier do that),
    and it is means that levels values are not consistent until Level modifier
    next call.

    Note: parent/children values integrity must be guaranteed by any modifier.
    Note: Level adds "level" and "level_original" attributes to any node.
    """
    modify_event = ONCE | DEFAULT

    def modify(self, request, data, meta, **kwargs):
        # a bit of optimizations
        if (DEFAULT == meta['modify_event'] and
                not meta['modified_ancestors']):
            return

        # rebuild mode: add level values to new nodes and exit
        if ONCE == meta['modify_event'] and meta['rebuild_mode']:
            for node in data.get('rebuilt_nodes', []):
                for i in tgenerator(node.children):
                    i.level = i.parent.level + 1
                    i.level_original = i.level
            return

        for node in data['nodes']:
            node.level = 0
            for i in tgenerator(node.children):
                i.level = i.parent.level + 1

        # save original level value on ONCE event
        if ONCE == meta['modify_event']:
            for i in tgenerator(data['nodes']):
                i.level_original = i.level


class Jump(Modifier):
    """Clone child url to parent if parent is marked as "jump", recursive."""
    modify_event = ONCE | PER_REQUEST

    def modify(self, request, data, meta, **kwargs):
        # a bit of optimizations
        if (PER_REQUEST == meta['modify_event'] and
            not meta['modified_descendants']) or (
                ONCE == meta['modify_event'] and meta['rebuild_mode'] and
                not [i for i in data.get('rebuilt_nodes', [])
                     if i.data.get('jump', False)]):
            return

        chain = []
        for node in tgenerator(data['nodes']):
            if node.children and node.data.get('jump', False):
                chain.append(node)
            elif chain:
                chain.append(node)
                self.clone_url(chain)
                chain = []

        if chain:
            self.clone_url(chain)

    def clone_url(self, chain):
        for node in chain[:-1]:
            node.url = chain[-1].url


class AuthVisibility(Modifier):
    """Remove nodes that are required an auth."""
    modify_event = PER_REQUEST

    def modify(self, request, data, meta, **kwargs):
        # if user is authenticated, allow all nodes
        if request.user.is_authenticated():
            return

        temp = {'count': 0,}  # in closure

        def checker(node):
            if node.data.get('auth_required', False):
                temp['count'] += 1
                return False
            return True

        # cut auth_required nodes (all or only rebuilt)
        nodes = ([i.children for i in data.get('rebuilt_nodes', [])]
                 if meta['rebuild_mode'] else [data['nodes']])
        for i in nodes:
            tcutter(i, checker)

        temp['count'] and meta.update(modified_descendants=True)


class NavigationExtender(Modifier):
    """Extends menu item with another menu."""
    modify_event = ONCE

    def modify(self, request, data, meta, **kwargs):
        # a bit of optimizations
        if meta['rebuild_mode']:
            return

        nodes, processed = data['nodes'], []
        for node in tgenerator(nodes):
            extenders = node.data.get("navigation_extenders", None)
            if not extenders:
                continue
            for extender in extenders:
                if extender in processed:
                    continue
                processed.append(extender)
                for n in nodes:  # process root nodes with extenders
                    if n.namespace == extender:
                        n.parent = node
                        node.children.append(n)
        # filter root nodes if any processed extenders
        if processed:
            nodes[:] = [i for i in nodes if not i.parent]
        data['nodes'] = nodes


class MetaDataProcessor(Modifier):
    modify_event = POST_SELECT

    def modify(self, request, data, meta, **kwargs):
        selected = data['selected']
        chain = [i for i in (data['chain'] or [])
                 if i.data.get('visible_in_chain', True)]

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


class PositionalMarker(Modifier):
    """
    Marker adds "sibling", "ancestor", "descendant", "selected"
    and "leaf" attributes to any node.
    """
    modify_event = ONCE | POST_SELECT

    def modify(self, request, data, meta, **kwargs):
        """
        On ONCE just add required attributes.
        On POST_SELECT mark leaf nodes and if selected exists,
            mark siblings, ancestors and descendants.
        """

        nodes, selected = data['nodes'], data['selected']

        if (ONCE == meta['modify_event']):
            nodes = (data.get('rebuilt_nodes', [])
                     if meta['rebuild_mode'] else nodes)
            for node in tgenerator(nodes):
                node.sibling = node.leaf = False
                node.ancestor = node.descendant = False
            return

        # mark leafs # does it really need?
        for node in tgenerator(nodes):
            node.leaf = not node.children

        if not selected:
            return

        # mark siblings
        siblings = selected.parent.children if selected.parent else nodes
        for i in siblings:
            i.sibling = not i.selected

        # mark ancestors
        ancestor = selected
        while ancestor.parent:
            ancestor = ancestor.parent
            ancestor.ancestor = True

        # mark descendants
        for i in tgenerator(selected.children):
            i.descendant = True


class CutLevels(Modifier):
    """
    Filters nodes by its level and/or visible value.
    Depends on PositionalMarker if root descendants expected.
    """
    modify_event = DEFAULT

    # !!! VISIBILITY
    def modify(self, request, data, meta, **kwargs):
        """
        Cut nodes by levels away from menus, also check visibility.
        Modifier waits "cut_levels" kwargs key, which contains all required
        values: (from_level, to_level, extra_inactive, extra_active,
                 extra_active_mode, show_invisible, show_inactive_branch)
        Algorithm:
        1. Get selected trail.
        3. Cut inactive root in range from_level..to_level|extra_inactive.
        3. Process root trail node.
            3.1. Cut active after to_level|extra_active with considering
                 of extra_active_mode value.
            3.2. Cut root active node before from_level.
            3.3. Cut inactive in active branch after to_level|extra_inactive.
        4. Cut active root if descendant property set to True.
        """

        # get argumets from cut_levels keyword argumet
        cut_levels = kwargs.get('cut_levels', None)
        if (not cut_levels or not isinstance(cut_levels, dict) or
                not len(cut_levels) == 7 or not data['nodes']):
            return

        (from_level, to_level, extra_inactive, extra_active, extra_active_mode,
         show_invisible, show_inactive_branch,) = map(cut_levels.get, [
             'from_level', 'to_level', 'extra_inactive', 'extra_active',
             'extra_active_mode', 'show_invisible', 'show_inactive_branch',
         ])

        # nodes current state values
        nodes, chain = data['nodes'], data['chain']

        # (1) search for selected trail
        trail = chain and self.get_trail(nodes, chain)

        # get level values related to selected node
        from_level, to_level, extra_inactive, extra_active = self.parse_params(
            trail, chain, from_level, to_level, extra_inactive, extra_active)

        # check: show only active branch - ignore nodes on from_level
        # from inactive branches (not sel-sib-desc or with ancestor parent)
        only_active_branch = (not show_inactive_branch and from_level > 0)

        # process nodes with algorithm
        final = []
        for node in nodes:
            if trail and node == trail[0]:
                # (3) process trail (active branch)
                items = self.cut_before_and_after_active(
                    trail, from_level, to_level, extra_inactive, extra_active,
                    extra_active_mode, only_active_branch, show_invisible)
            elif getattr(node, 'descendant', True):
                # (4) cut active root if it descendant
                items = self.cut_before_and_after(
                    node, from_level, to_level, extra_active,
                    False, show_invisible)
            else:
                # (2) cut inactive in from_level..to_level|extra_active
                items = self.cut_before_and_after(
                    node, from_level, to_level, extra_inactive,
                    only_active_branch, show_invisible)
            final.extend(items)

        # update meta information and nodes data
        meta.update(
            modified_ancestors=from_level or meta['modified_ancestors'],
            modified_descendants=True  # let it be modified anyway
        )

        data['nodes'] = final
        return data

    def cut_after(self, node, current_level, to_level, show_invisible=False):
        """Cut nodes from tree after specified level."""
        if not node.children:
            return
        elif to_level <= current_level:
            node.children = []
        else:
            if not show_invisible:
                node.children = [i for i in node.children if i.visible]
            for n in node.children:
                n.children and self.cut_after(n, current_level+1, to_level)
        return node

    def cut_before_and_after(self, node, from_level, to_level, extra_level,
                             only_active_branch, show_invisible):
        """Cut node in range from_level..to_level|extra_level"""
        # empty on active branch only or unconditional cut by range
        if only_active_branch or from_level > to_level:
            return []

        # cut before from_level
        level, final = 0, [node]
        while level < from_level:
            final, line, level = [], final, level+1
            for i in line:
                final.extend(i.children)
                for j in i.children:
                    j.parent = None

        # check visibility in from_level
        if not show_invisible:
            final = [i for i in final if i.visible]

        # cut after to_level|extra_level
        for i in final:
            self.cut_after(i, level, min(to_level, extra_level),
                           show_invisible)
        return final

    def cut_after_active(self, node, trail, to_level, show_invisible):
        """Cut inactive from trail in range index-of-node..last-but-one."""
        index = trail.index(node)
        while index < len(trail)-1:  # exclude last of trail elements
            node, index = trail[index], index+1
            if not show_invisible:
                node.children = [i for i in node.children if i.visible]
            for i in node.children:
                i not in trail and self.cut_after(i, index, to_level)

    def cut_before_and_after_active(self, trail, from_level, to_level,
                                    extra_inactive, extra_active,
                                    extra_active_mode, only_active_branch,
                                    show_invisible):
        """
        Cut active node in range from_level..to_level|extra_active with
        considering of extra_active_mode and inactive in active branch
        in range from_level..to_level|extra_inactive.
        """

        # empty on unconditional cut by range
        if from_level > to_level:
            return []

        extra_inactive = min(to_level, extra_inactive)
        extra_active = min((extra_active if extra_active_mode else
                            max(extra_active, len(trail)-1), to_level))
        extra_active_strict = (extra_active_mode != 2 or
                               to_level <= extra_active or
                               extra_inactive <= extra_active)

        # check visibility in trail
        if not show_invisible:
            for i in trail:
                if not i.visible:
                    i.parent and i.parent.children.remove(i)
                    trail[trail.index(i):] = []
                    if not trail:
                        return []
                    break

        # (3.1.) cut extra_active
        if extra_active < len(trail)-1:
            # reduce trail and cut with considering of extra_active_mode
            trail[extra_active].children = [] if extra_active_strict else [
                self.cut_after(i, extra_active+1, extra_inactive,
                               show_invisible)
                for i in trail[extra_active].children
                if i not in trail and (show_invisible or i.visible)
            ]
            trail[extra_active+1:] = []
            active_branch = set(trail)
        else:
            # just cut after selected and add all descendant into set
            self.cut_after(trail[-1], len(trail)-1, extra_active,
                           show_invisible)
            active_branch = (set(trail) if from_level < len(trail) else
                             set(trail + list(tgenerator(trail[-1].children))))

        # (3.2.) cut before from_level
        level, final = 0, [trail[0]]
        while level < from_level:
            final, line, level = [], final, level+1
            for i in line:
                children = [j for j in i.children
                            if not only_active_branch or j in active_branch]
                final.extend(children)
                for j in children:
                    j.parent = None

        # check visibility in from_level
        if not show_invisible:
            final = [i for i in final if i.visible]
        # (3.3.) cut inactive in active branch after to_level|extra_inactive
        for i in final:
            if i not in active_branch:
                self.cut_after(i, level, min(to_level, extra_inactive),
                               show_invisible)
            elif i in trail:
                self.cut_after_active(i, trail, min(to_level, extra_inactive),
                                      show_invisible)

        return final

    def get_trail(self, nodes, chain):
        """
        Get selected or closest to selected ancestor, presented in nodes,
        and all its ancestors.
        """
        index = len(chain)
        while index:
            snode = chain[index-1]
            trail = [snode]
            while snode.parent:
                snode = snode.parent
                trail.insert(0, snode)
            if trail[0] in nodes:
                return trail
            index -= 1
        return []

    def parse_params(self, trail, chain, *params):
        """
        Process params with {so} and {s} patterns, if defined.
        Allowed values:
            (0, 10, 10, 10,)                - direct integer values,
            ({s}, {s}+10, {so}+1, {so}+10,) - expressions (see below)

        Values should contains only digits, [+-] signs and {s}, {so}
        patterns (no space allowed), which are selected (deepest chain node
        detected in nodes) and selected-original (real original level value)
        level values respectively. If value is invalid - it will be set to 0.
        """

        # get selected-original, selected
        so, s = (len(chain)-1, len(trail)-1) if chain else (0, 0,)

        # params as list for direct assignation (*args are tuple)
        params = list(params)

        # process each params
        for i, param in enumerate(params):
            if isinstance(param, int) and param >= 0:
                continue
            param = (str(param).format(so=so, s=s) or '0') if param else '0'
            value = (eval(param)
                     if param.replace('+', '').replace('-', '').isdigit()
                     else 0)
            params[i] = value if value > 0 else 0

        return params
