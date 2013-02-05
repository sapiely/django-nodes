from django import template
from menus.template import inclusion_tag_ex, get_from_context
from menus import registry

def show_menu(context, from_level=0, to_level=100, extra_inactive=0, extra_active=100,
                        template=None, namespace=None, root_id=None,
                         show_unvisible=False, show_inactive_branch=False, menuconf=None):
    """
    render a nested list of all children of the pages
    - from_level: starting level
    - to_level: max level
    - extra_inactive: how many levels should be rendered of the not active tree?
    - extra_active: how deep should the children of the active node be rendered?
    - template: template used to render the menu
    - namespace: the namespace of the menu. if empty will use all namespaces
    - root_id: the id of the root node
    - show_unvisible: show nodes marked as hidden
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
    if not nodes: return {'template': template}

    # cut levels and apply_modifiers in post_cut mode
    fr_l, to_l, e_in, e_ac = parse_params(nodes, from_level, to_level,
                                                  extra_inactive, extra_active)
    children, selected = cut_levels(nodes, fr_l, to_l, e_in, e_ac, show_unvisible,
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
                       show_unvisible=False, show_inactive_branch=False):
    """cutting nodes by levels away from menus, also check visibility, ect"""

    # default values
    final, removed, selected, in_branch = [], {}, None, False
    # check: show only active branch (see below)
    only_active_branch = not show_inactive_branch and nodes[0].level < from_level

    # main loop
    for node in nodes:
        # ignore nodes, which already is removed
        if node.id in removed: continue
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
        # remove and ignore nodes that don't have level information
        if not hasattr(node, 'level'):
            remove(node, removed)
            continue
        # turn nodes that are on from_level into root nodes
        if node.level == from_level:
            final.append(node)
            node.parent = None
            # cut inactive nodes to extra_inactive (nodes in not active branch)
            if not (node.selected or node.ancestor or node.descendant):
                node.children and cut_after(node, extra_inactive, removed)
        # remove nodes that are too deep
        if node.level > to_level:
            remove(node, removed)
        # save selected node
        if node.selected:
            selected = node
        # hide node if required
        if not show_unvisible and not node.visible:
            remove(node, removed)

    # cut active nodes to extra_active (nodes in active branch)
    if selected:
        node.children and cut_after(selected, extra_active, removed)

    # remove marked-for-remove zero-level nodes
    if removed:
        ftemp, final = final, []
        for node in ftemp:
            if node.id in removed: continue
            final.append(node)

    return final, selected

def cut_after(node, levels, removed):
    """given a tree of nodes cuts after N levels"""
    if levels == 0:
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

def parse_params(nodes, *params):
    """process params with - or + or = if defined"""
    check = lambda x: not isinstance(x, int) or x < 0
    if not filter(check, params): return params

    # todo: optimise selected node retieve, may be cahce it?
    current = registry.menupool._get_selected(nodes)
    current, params = current.level if current else 0, list(params)

    operations = {'+': int.__add__, '-': int.__sub__}
    for i in range(0, len(params)):
        if not check(params[i]): continue
        param = params[i].__str__()
        if param[0] == '=':
            value = current
        else:
            value = param.strip('+-')
            value = int(value) if value and value.isdigit() else 0
            value = operations.get(param[0], operations['+'])(current, value)
        params[i] = value if value > 0 else 0
    return params

register = template.Library()
load_menu = register.tag(load_menu)
inclusion_tag_ex(register, takes_context=True)(show_menu)
inclusion_tag_ex(register, takes_context=True)(show_breadcrumb)