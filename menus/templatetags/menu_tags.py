from django import template
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import activate, get_language, ugettext
from menus.template import simple_tag_ex, inclusion_tag_ex, get_from_context
from menus.menu_pool import menu_pool

def show_menu(context, from_level=0, to_level=100, extra_inactive=0, extra_active=100,
               template=None, namespace=None, root_id=None,
                show_unvisible=False, show_inactive_branch=False):
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
    """

    # set template by default
    template = template or "menus/menu.html"
    # if there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}
    # get nodes (by root and/or by namespace if defined)
    nodes = menu_pool.get_nodes(request, namespace, root_id)
    if not nodes: return {'template': template}

    from_level, to_level, extra_inactive, extra_active = parse_params(nodes, from_level, to_level, extra_inactive, extra_active)
    children = cut_levels(nodes, from_level, to_level, extra_inactive, extra_active, show_unvisible, show_inactive_branch)
    children = menu_pool.apply_modifiers(children, request, namespace, root_id, post_cut=True)

    context.update({'children':children,
                    'template':template,
                    'from_level':from_level,
                    'to_level':to_level,
                    'extra_inactive':extra_inactive,
                    'extra_active':extra_active,
                    'namespace':namespace})
    return context

def show_breadcrumb(context, start_level=0, template="menus/breadcrumb.html"):
    """
    Shows the breadcrumb from the node that has the same url as the current request
    - start level: after which level should the breadcrumb start? 0=home
    - template: template used to render the breadcrumb
    """

    # if there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}

    nodes = menu_pool.get_nodes(request)
    chain = menu_pool._get_full_chain(nodes, menu_pool._get_selected(nodes))
    chain = chain[start_level:] if len(chain) >= start_level else []
    context.update({'chain': chain, 'template': template})
    return context

def load_menu(parser, token):
    """loads menu, set data to request.meta first"""
    class LoadMenuNode(template.Node):
        def render(self, context):
            request = get_from_context(context, 'request')
            menu_pool.get_nodes(request, init_only=True)
            return ''
    return LoadMenuNode()

def cut_levels(nodes, from_level, to_level, extra_inactive, extra_active,
                show_unvisible=False, show_inactive_branch=False):
    """cutting nodes away from menus"""
    final, removed, selected, in_branch = [], {}, None, False
    root_level, only_active_branch = nodes[0].level, not show_inactive_branch and nodes[0].level < from_level
    for node in nodes:
        # ignore nodes, which already is removed
        if node.id in removed: continue
        # check only active branch if some conditions
        if only_active_branch:
            if not in_branch and node.level == from_level:
                in_branch = node.selected or node.ancestor or node.descendant
            elif in_branch and node.level == root_level:
                break
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
        if root_level == node.level and not any((node.ancestor, node.selected, node.descendant)):
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
    if selected:
        node.children and cut_after(selected, extra_active, removed)
    if removed:
        ftemp, final = final, []
        for node in ftemp:
            if node.id in removed: continue
            final.append(node)

    return final

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

    current = menu_pool._get_selected(nodes)
    current, params = current.level if current else 0, list(params)
    operations = {'+': int.__add__, '-': int.__sub__}
    for i in range(0, len(params)):
        if not check(params[i]): continue
        param = params[i].__str__()
        if param[0] == '=':
            value = current
        else:
            value, sign = param.strip('+-'), param[0] if param[0] in ['+', '-'] else '+'
            value = int(value) if value and value.isdigit() else 0
            value = operations[sign](current, value)
        params[i] = value if value > 0 else 0
    return params

register    = template.Library()
load_menu   = register.tag(load_menu)
inclusion_tag_ex(register, takes_context=True, asis_params=True)(show_menu)
inclusion_tag_ex(register, takes_context=True)(show_breadcrumb)