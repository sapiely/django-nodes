from django import template
from django.conf import settings
from django.utils.translation import activate, get_language, ugettext
from django.core.cache import cache
from nodes.menus.template import simple_tag_ex, inclusion_tag_ex, get_from_context
from nodes.menus.menu_pool import menu_pool

def show_menu(context, from_level=0, to_level=100, extra_inactive=0, extra_active=100, 
                template="menus/menu.html", namespace=None, root_id=None, show_unvisible=False):
    """
    render a nested list of all children of the pages
    - from_level: starting level
    - to_level: max level
    - extra_inactive: how many levels should be rendered of the not active tree?
    - extra_active: how deep should the children of the active node be rendered?
    - template: template used to render the menu
    - namespace: the namespace of the menu. if empty will use all namespaces
    - root_id: the id of the root node
    """

    # If there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}
    # set template by default
    template = template or "menus/menu.html"
    # new menu... get all the data so we can save a lot of queries
    nodes = menu_pool.get_nodes(request, namespace, root_id)
    # get nodes in root if defined
    if root_id:
        nodes, from_level = nodes_in_root(nodes, root_id, from_level)

    children = cut_levels(nodes, from_level, to_level, extra_inactive, extra_active, show_unvisible)
    children = menu_pool.apply_modifiers(children, request, namespace, root_id, post_cut=True)

    context.update({'children':children,
                    'template':template,
                    'from_level':from_level,
                    'to_level':to_level,
                    'extra_inactive':extra_inactive,
                    'extra_active':extra_active,
                    'namespace':namespace})
    return context

def show_menu_below_id(context, root_id=None, from_level=0, to_level=100, extra_inactive=100, extra_active=100, template_file="menus/menu.html", namespace=None):
    """displays a menu below a node that has an uid"""
    return show_menu(context, from_level, to_level, extra_inactive, extra_active, template_file, root_id=root_id, namespace=namespace)

def show_sub_menu(context, levels=100, template="menus/sub_menu.html"):
    """
    show the sub menu of the current nav-node.
    -levels: how many levels deep
    -temlplate: template used to render the navigation
    """

    # If there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}

    nodes = menu_pool.get_nodes(request)
    children = []
    for node in nodes:
        if node.selected:
            cut_after(node, levels, [])
            children = node.children
            for child in children:
                child.parent = None
            children = menu_pool.apply_modifiers(children, request, post_cut=True)
    context.update({'children':children,
                    'template':template,
                    'from_level':0,
                    'to_level':0,
                    'extra_inactive':0,
                    'extra_active':0
                    })
    return context

def show_breadcrumb(context, start_level=0, template="menus/breadcrumb.html"):
    """
    Shows the breadcrumb from the node that has the same url as the current request

    - start level: after which level should the breadcrumb start? 0=home
    - template: template used to render the breadcrumb
    """

    # If there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request: return {'template': 'menus/empty.html'}

    nodes = menu_pool.get_nodes(request, breadcrumb=True)
    chain = menu_pool._get_full_chain(nodes)

    if len(chain) >= start_level:
        chain = chain[start_level:]
    else:
        chain = []
    context.update({'chain': chain,
                    'template': template})
    return context

def nodes_after_node(node, result, unparent=False):
    if not node.children:
        return result
    for n in node.children:
        result.append(n)
        if unparent:
            n.parent = None
        if n.children:
            result = nodes_after_node(n, result)
    return result

def nodes_in_root(nodes, root_id, from_level):
    """get nodes in node with reverse_id == root_id"""    
    new_nodes = []
    id_nodes = menu_pool.get_nodes_by_attribute(nodes, "reverse_id", root_id)
    if id_nodes:
        new_nodes = nodes_after_node(id_nodes[0], [], unparent=True)
        # set from_level to level of root (important in cut_levels)
        from_level = id_nodes[0].level
    return new_nodes, from_level

def cut_after(node, levels, removed):
    """given a tree of nodes cuts after N levels"""
    if levels == 0:
        for n in node.children:
            removed.append(n)
            cut_after(n, 0, removed)
        node.children = []
    else:
        for n in node.children:
            cut_after(n, levels-1, removed)

def remove(node, removed):
    """remove node"""
    removed.append(node)
    if node.parent:
        if node in node.parent.children:
            node.parent.children.remove(node)

def cut_levels(nodes, from_level, to_level, extra_inactive, extra_active, show_unvisible=False):
    """cutting nodes away from menus"""
    final, removed, selected, in_branch = [], [], None, False
    from_gt_root = nodes[0].level < from_level
    for node in nodes:
        # check only selected branch if from_level > level of root nodes
        if from_gt_root:
            if not in_branch and node.level+1 == from_level:
                in_branch = node.ancestor or node.selected
            elif in_branch and node.level < from_level:
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
        # cut inactive nodes to extra_inactive, but not of descendants of the selected node
        if not node.ancestor and not node.selected and not node.descendant:
            cut_after(node, extra_inactive, removed)
        # remove nodes that are too deep
        if node.level > to_level and node.parent:
            remove(node, removed)
        if node.selected:
            selected = node
        if not show_unvisible and not node.visible:
            # cut_after(node, 0, removed) # may be
            remove(node, removed)
    if selected:
        cut_after(selected, extra_active, removed)
    if removed:
        for node in removed:
            if node in final:
                final.remove(node)
    return final

def load_menu(parser, token):
    """loads menu, set data to request.meta first"""
    class LoadMenuNode(template.Node):
        def render(self, context):
            request = get_from_context(context, 'request')
            menu_pool.get_nodes(request)
            return ''
    return LoadMenuNode()

register    = template.Library()
load_menu   = register.tag(load_menu)
inclusion_tag_ex(register, takes_context=True)(show_menu)
inclusion_tag_ex(register, takes_context=True)(show_menu_below_id)
inclusion_tag_ex(register, takes_context=True)(show_sub_menu)
inclusion_tag_ex(register, takes_context=True)(show_breadcrumb)