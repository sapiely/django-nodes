from django import template
from menus.template import inclusion_tag, get_from_context
from menus import registry
import re

def show_menu(context, from_level=0, to_level=100, extra_inactive=0, extra_active=100,
                        template=None, namespace=None, root_id=None,
                         show_invisible=False, show_inactive_branch=False, menuconf=None):
    """
    render a nested list of all children of the pages
    - from_level: starting level
    - to_level: max level
    - extra_inactive: how many levels should be rendered of the not active tree?
    - extra_active: how deep should the children of the active node be rendered?
    - template: template used to render the menu
    - namespace: the namespace of the menu. if empty will use all namespaces
    - root_id: the id of the root node
    - show_invisible: show nodes marked as hidden
    - show_inactive_branch: show nodes in inactive branch (use when from_level > 0)
    - menuconf: menuconf name, usually retrieve implicitly by routing
    """

    # set template by default
    template = template or "menus/menu.html"
    # if there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html',}

    # get pre-cut nodes (by menuconf and/or root_id and/or namespace if defined)
    menuconf = registry.menupool.menuconf(request, name=menuconf)
    nodes = registry.menupool.get_nodes(menuconf, request, namespace=namespace,
                                                            root_id=root_id)
    if not nodes: return {'template': template,}

    # cut levels and apply_modifiers in post_cut mode
    fr_l, to_l, e_in, e_ac = parse_params(request, nodes, from_level, to_level,
                                                           extra_inactive, extra_active)
    children, selected = cut_levels(nodes, fr_l, to_l, e_in, e_ac, show_invisible,
                                                                    show_inactive_branch)
    children = registry.menupool.apply_modifiers(menuconf, children, request,
                                                  namespace=namespace, root_id=root_id,
                                                   post_cut=True)

    context.update({'children': children,
                     'selected': selected,
                      'template': template,
                       'namespace': namespace,
                        'from_level': fr_l,
                         'to_level': to_l,
                          'extra_inactive': e_in,
                           'extra_active': e_ac,})
    return context

def show_breadcrumb(context, start_level=0, template="menus/breadcrumb.html"):
    """
    Shows the breadcrumb from the node that has the same url as the current request
    - start level: after which level should the breadcrumb start? 0=home
    - template: template used to render the breadcrumb
    note: this is very native method - use show_meta_chain instead
    """

    # if there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}

    menuconf = registry.menupool.menuconf(request)
    nodes = registry.menupool.get_nodes(menuconf, request)
    current = registry.menupool._get_selected(nodes)
    chain = registry.menupool._get_full_chain(nodes, current)
    chain = chain[start_level:] if len(chain) >= start_level else []
    context.update({'chain': chain, 'template': template})
    return context

def load_menu(parser, token):
    """loads menu, set data to request.meta first"""
    class LoadMenuNode(template.Node):
        def render(self, context):
            request = get_from_context(context, 'request')
            registry.menupool.get_nodes(None, request, init_only=True)
            return ''
    return LoadMenuNode()

# utils
def cut_levels(nodes, from_level, to_level, extra_inactive, extra_active,
                       show_invisible=False, show_inactive_branch=False):
    """cutting nodes by levels away from menus, also check visibility, ect"""

    # default values
    final, removed, selected, in_branch = [], {}, None, False
    # check: show only active branch (see below)
    only_active_branch = not show_inactive_branch and nodes[0].level < from_level

    # main loop
    for node in nodes:
        # ignore nodes, which already is removed
        if node.id in removed: continue
        # remove and ignore nodes that don't have level information
        if not hasattr(node, 'level'):
            remove(node, removed)
            continue

        # save selected node
        if node.selected:
            selected = node

        # check only active branch if some conditions
        if only_active_branch:
            # check node is in selected branch: directry by sel-sib-des attrs
            #                                            or via parent.ancestor
            if not in_branch and node.level == from_level:
                in_branch = node.descendant or node.parent.ancestor \
                                            or node.sibling or node.selected
            # node is out of the selected branch, out of from_level > break
            elif in_branch and node.level < from_level:
                break
            # just ignore left side relative to selected branch
            if not in_branch:
                continue
        # ignore nodes higher then from level
        elif node.level < from_level:
            continue

        # remove nodes that are too deep or invisible (show_visible mode is off)
        if (node.level > to_level) or (not show_invisible and not node.visible):
            remove(node, removed)
            continue

        # cut inactive nodes to extra_inactive (nodes in not active branch)
        if not (node.selected or node.ancestor or node.descendant) and node.children:
            cut_after(node, extra_inactive, removed)
        # turn nodes that are on from_level into root nodes
        if node.level == from_level:
            final.append(node)
            node.parent = None

    # remove marked-for-remove zero-level nodes
    if removed:
        ftemp, final = final, []
        for node in ftemp:
            if node.id in removed: continue
            final.append(node)

    # cut active nodes to extra_active (nodes in active branch)
    if selected and selected.children:
        cut_after(selected, extra_active, removed)
    elif not selected:
        for node in final:
            node.descendant and cut_after(node, extra_active, removed)

    return final, selected

def cut_after(node, levels, removed):
    """given a tree of nodes cuts after N levels"""
    if not node.children:
        return
    elif levels <= node.level: # relative to current node
        for n in node.children:
            removed.__setitem__(n.id, None)
            n.children and cut_after(n, 0, removed)
        node.children = []
    else:
        for n in node.children:
            n.children and cut_after(n, levels-1, removed)

def remove(node, removed):
    """remove node"""
    removed.__setitem__(node.id, None)
    if node.parent and node in node.parent.children:
        node.parent.children.remove(node)
    node.children and cut_after(node, 0, removed)

def parse_params(request, nodes, *params):
    """
    process params with +-=, : or @ if defined:
    [0, 1, 2, 3]    - direct values
    [:c+1, :co-1, :c-r, :co-ro+1]
                    - expression of current, current-original,
                                       root, root-original
    [+1 -1 =]       - aliases to :c+1 :c-1 :c
    
    todo: [@name|+1]- lambda with name and following params:
                       nodes, request, value param (here is +1)
    """

    check = lambda x: not (isinstance(x, int) and x >= 0)
    CHECK = re.compile('^([+-]?(?:ro?|co?|\d))+$')
    if not filter(check, params): return params

    # todo: optimise selected node retieve, may be cahce it?
    root = nodes and nodes[0] or None
    current = registry.menupool._get_selected(nodes)

    # get expression params: current-original, current, root-original, root
    co = request.meta.current and request.meta.current.level or 0
    c = current and current.level or 0
    ro = root and root.attr.get('levelorig', root.level or 0)
    r = root and root.level or 0

    # current level and params as list for direct assignation
    current, params = current.level if current else 0, list(params)

    # process each params
    for i in range(0, len(params)):
        if not check(params[i]): continue
        param = params[i].__str__() or '0'

        # alias process
        if param[0] == '=':
            param = ':c'
        elif param[0] in '+-':
            param = ':c%s' % param

        # eval if valid expression else int value
        if param[0] == ':' and CHECK.match(param[1:]):
            value = eval(param[1:])
        else:
            value = int(value) if param.isdigit() else 0

        params[i] = value if value > 0 else 0

    return params

register = template.Library()
load_menu = register.tag(load_menu)
inclusion_tag(register, takes_context=True)(show_menu)
inclusion_tag(register, takes_context=True)(show_breadcrumb)
