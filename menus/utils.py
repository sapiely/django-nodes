from importlib import import_module

def add_nodes_to_request(request):
    from .. import reqistry
    reqistry.menupool.add_nodes_to_request(request)

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
