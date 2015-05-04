from sakkada.admin.fkey_list import FkeyListAdmin, FkeyMpttAdmin, fkey_list_link
from sakkada.admin.mptt_tree import MpttTreeAdmin
from sakkada.admin.ajax_list import AjaxListAdmin, ajax_list_field
from nodes.admin import NodeAdmin, ItemAdmin


class NodeNiceAdmin(AjaxListAdmin, MpttTreeAdmin, FkeyMpttAdmin, NodeAdmin):
    # add to display ajax booleans and fkey_list links
    list_display = (
        'indented_short_title', 'id', 'move_node_column',
        'item_link', 'node_link', 'slug',  'level',
        'toggle_active', 'toggle_menu_in', 'toggle_menu_in_chain',
        'toggle_menu_jump', 'toggle_menu_login', 'toggle_menu_current',
    )

    ajax_list_parent_template = 'admin/mptt_tree/change_list.html'
    mptt_tree_parent_template = 'admin/fkey_list/change_list.html'

    # ajax_list ajax boolean
    toggle_active           = ajax_list_field('active', 'active?')
    toggle_menu_in          = ajax_list_field('menu_in', 'menu in?')
    toggle_menu_in_chain    = ajax_list_field('menu_in_chain', 'chain in?')
    toggle_menu_jump        = ajax_list_field('menu_jump', 'jump?')
    toggle_menu_login       = ajax_list_field('menu_login_required', 'login?')
    toggle_menu_current     = ajax_list_field('menu_show_current', 'h1 title?')

    # fkey_list links
    item_link = fkey_list_link('item', model_set='item_set',
                               fkey_name='node', with_add_link=True)
    node_link = fkey_list_link('node', model_set='children',
                               fkey_name='parent', with_add_link=True)

    # mptt_tree: pass is_moved into save
    def save_moved_node(self, node):
        return node.save(is_moved=True)

    # mptt_tree indented title with fkey_list links
    def indented_short_title_text(self, item):
        return '%s %s' % (
            u'<a href="%s" title="show related elements">%s</a>' \
             % (self.item_link(item, url_only='list'),  unicode(item),),
            u'<nobr>(<a href="%s/" title="edit &laquo;%s&raquo;">edit</a>)</nobr>' \
             % (item.pk, item.__class__._meta.verbose_name,),
        )


class ItemNiceAdmin(AjaxListAdmin, FkeyListAdmin, ItemAdmin):
    ajax_list_parent_template = 'admin/fkey_list/change_list.html'

    # add to display ajax booleans
    list_display = (
        'name', 'id', 'slug', 'sort',
        'toggle_active', 'toggle_visible', 'toggle_show_item_name',
        'toggle_show_node_link', 'toggle_show_in_meta',
    )

    # ajax_list ajax boolean
    toggle_active           = ajax_list_field('active', 'active?')
    toggle_visible          = ajax_list_field('visible', 'visible?')
    toggle_show_item_name   = ajax_list_field('show_item_name', 'name?')
    toggle_show_node_link   = ajax_list_field('show_node_link', 'to list?')
    toggle_show_in_meta     = ajax_list_field('show_in_meta', 'meta?')
