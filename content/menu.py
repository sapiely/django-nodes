from menus import registry
from nodes.menu import NodeMenu
from models import NodeMain


class NodeMainMenu(NodeMenu):
    model_class = NodeMain

# register menu class(es)
registry.register_menu(NodeMainMenu)
