from menus.base import Menu, NavigationNode, Modifier
from django.contrib.sites.models import Site

def page_to_node(node):
    attr = {
        'reverse_id': '%s_%s' % (node.__class__.__name__.lower(), node.pk),
        'auth_required': node.menu_login_required,
        'show_meta_current': node.menu_show_current,
        'jump': node.menu_jump,
    }
            
    if node.menu_extender:
        attr['navigation_extenders'] = node.menu_extender
    n = NavigationNode(
        node.get_menu_title(),
        node.get_absolute_url(),
        node.pk,
        node.parent_id,
        visible=node.menu_in,
        visible_chain=node.menu_in_chain,
        meta_title=node.meta_title or node.name,
        meta_keywords=node.meta_keywords,
        meta_description=node.meta_description,
        attr=attr,
    )
    return n

class NodeMenu(Menu):
    model_class = None
    def get_nodes(self, request):
        if not self.model_class:
            raise Exception, 'model_class variable not defined in NodeMenu'
        site = Site.objects.get_current()
        pages = self.model_class.objects.filter(site=site).order_by("tree_id", "lft")
        nodes, home, cut_branch, cut_level = [], None, False, None
        for page in pages:
            # remove inactive nodes
            if cut_branch:
                if cut_level < page.level: continue
                cut_branch = False
            if not page.active:
                cut_branch = True
                cut_level = page.level
                continue
            nodes.append(page_to_node(page))
        return nodes