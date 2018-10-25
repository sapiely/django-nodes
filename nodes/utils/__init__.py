from importlib import import_module


def add_nodes_to_request(request):
    from .. import registry
    registry.processor.add_nodes_to_request(request)

def import_path(import_path, alternate=None):
    """import module by import_path"""
    try:
        module_name, value_name = import_path.rsplit('.', 1)
        module = import_module(module_name)
        value_name = getattr(module, value_name)
    except ImportError:
        value_name = alternate
    except AttributeError:
        value_name = alternate
    return value_name


# hierarchical nodes handling
def tgenerator(nodes):
    """Unwrap hierarchical nodes struct into linear list."""
    for i in nodes:
        yield i
        if i.children:
            for i2 in i.children:
                yield i2
                if i2.children:
                    for i3 in i2.children:
                        yield i3
                        if i3.children:
                            for i4 in i3.children:
                                yield i4
                                if i4.children:
                                    for i5 in i4.children:
                                        yield i5
                                        if i5.children:
                                            for i6 in i5.children:
                                                yield i6
                                                if i6.children:
                                                    for deeper in tgenerator(
                                                            i6.children):
                                                        yield deeper

def tcutter(nodes, function):
    """Cut tree by function."""
    for i in nodes[:]:
        if not function(i):
            nodes.remove(i)
        elif i.children:
            for i2 in i.children[:]:
                if not function(i2):
                    i.children.remove(i2)
                elif i2.children:
                    for i3 in i2.children[:]:
                        if not function(i3):
                            i2.children.remove(i3)
                        elif i3.children:
                            for i4 in i3.children[:]:
                                if not function(i4):
                                    i3.children.remove(i4)
                                elif i4.children:
                                    for i5 in i4.children[:]:
                                        if not function(i5):
                                            i4.children.remove(i5)
                                        elif i5.children:
                                            tcutter(i5.children, function)
    return nodes

def tfilter(nodes, function, final=None):
    """Filter tree by function."""
    start = final is None
    final = nodes if start else final
    for i in nodes[:]:
        if not function(i):
            nodes.remove(i)
            for c in i.children:
                c.parent = None
        elif not i.parent and not start:
            final.append(i) # put node as new root
        if i.children:
            for i2 in i.children[:]:
                if not function(i2):
                    i2.parent and i.children.remove(i2)
                    for c in i2.children:
                        c.parent = None
                elif not i2.parent:
                    final.append(i2) # put node as new root
                if i2.children:
                    for i3 in i2.children[:]:
                        if not function(i3):
                            i3.parent and i2.children.remove(i3)
                            for c in i3.children:
                                c.parent = None
                        elif not i3.parent:
                            final.append(i3) # put node as new root
                        if i3.children:
                            for i4 in i3.children[:]:
                                if not function(i4):
                                    i4.parent and i3.children.remove(i4)
                                    for c in i4.children:
                                        c.parent = None
                                elif not i4.parent:
                                    final.append(i4) # put node as new root
                                if i4.children:
                                    tfilter(i4.children, function, final)
    return final
