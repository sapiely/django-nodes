def meta_to_request(request):
    if not hasattr(request, 'meta'):
        class MetaInRequest(object): pass
        request.meta                = MetaInRequest()
        request.meta.current        = None
        request.meta.chain          = []
        request.meta.title          = []
        request.meta.keywords       = []
        request.meta.description    = []

def node_class_by_name(name, class_type='node'):
    """get node/item class by node name and class type"""
    if not class_type in ['item', 'node']:
        raise Exception('class_type must be one of (item, node)')

    try:
        class_name = class_type[0].upper() + class_type[1:] + name[0].upper() + name[1:]
        class_from = __import__('nodes.models', {}, {}, [class_name])
        class_inst = getattr(class_from, class_name, None)
    except ImportError:
        raise ImportError
        class_inst = None
    return class_inst

def views_ex_by_name(view_name, node_name, obj_type):
    """get views_ex by name"""
    view_name = '%s_%s' % (obj_type, view_name)
    try:
        views_ex = __import__('nodes.views_ex.%s' % node_name, {}, {}, [view_name])
        views_ex = getattr(views_ex, view_name, None)
    except ImportError:
        raise ImportError
    return views_ex

def jump_node_by_node(node):
    """search target node from node with menu_jump"""
    node_from, node_to = node, None
    while True:
        if node_from.menu_jump and node_from.children.count():
            node_to = node_from.children.all()[0]
        if node_to and node_to.menu_jump:
            node_from, node_to = node_to, None
        else:
            if not node_to and node_from != node:
                node_to = node_from
            break
    return node_to