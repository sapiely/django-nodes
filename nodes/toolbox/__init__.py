def meta_to_request(request):
    if not hasattr(request, 'meta'):
        class MetaInRequest(object): pass
        request.meta                = MetaInRequest()
        request.meta.current        = None
        request.meta.chain          = []
        request.meta.title          = []
        request.meta.keywords       = []
        request.meta.description    = []

def class_by_name_and_type(name, class_type='node'):
    """get node/item class by node name and class type"""
    if not class_type in ['item', 'node']:
        raise Exception('class_type must be one of (item, node)')
    try:
        class_name = class_type[0].upper() + class_type[1:] + name[0].upper() + name[1:]
        class_inst = __import__('nodes.models', {}, {}, [class_name])
        class_inst = getattr(class_inst, class_name, None)
    except ImportError:
        raise ImportError('Nodes error - unable to import "nodes.models" module.')
    if not class_inst:
        raise Exception('Nodes error - reqired class %s (%s, %s) not defined, check your url conf.' % (class_name, class_type, name))

    return class_inst

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