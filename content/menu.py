from menus.menu_pool import menu_pool
from nodes.menu import NodeMenu
from models import NodeMain

class NodeMainMenu(NodeMenu):
    model_class = NodeMain

# register all menu classes
menu_pool.register_menu(NodeMainMenu)