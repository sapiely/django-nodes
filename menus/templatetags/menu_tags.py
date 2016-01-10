import re
from django import template
from menus.template import inclusion_tag, get_from_context
from menus import registry

def show_menu(context, from_level=0, to_level=100,
              extra_inactive=0, extra_active=100,
              template=None, namespace=None, root_id=None,
              show_invisible=False, show_inactive_branch=False,
              menuconf=None, **kwargs):
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
    menupool = registry.menupool
    menuconf = menupool.menuconf(request, name=menuconf)
    nodes = menupool.get_nodes(menuconf, request, namespace=namespace,
                               root_id=root_id, **kwargs)
    if not nodes: return {'template': template,}

    # cut levels and apply_modifiers in post_cut mode
    fr_l, to_l, e_in, e_ac = parse_params(request, nodes, from_level, to_level,
                                          extra_inactive, extra_active)
    children, selected = menupool.cut_levels(nodes, fr_l, to_l, e_in, e_ac,
                                             show_invisible, show_inactive_branch)
    children = menupool.apply_modifiers(menuconf, children, request,
                                        namespace=namespace, root_id=root_id,
                                        post_cut=True, kwargs=kwargs)

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
