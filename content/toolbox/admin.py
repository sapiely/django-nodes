from sakkada.admin.fkey_list import FkeyListAdmin, FkeyMpttAdmin, fkey_list_link
from sakkada.admin.mptt_tree import MpttTreeAdmin, AjaxBoolAdmin, ajax_boolean
from sakkada.admin.cache_clear import CacheClearAdmin
from nodes.admin import NodeAdmin, ItemAdmin
import copy

class NodeNiceAdmin(CacheClearAdmin, MpttTreeAdmin, FkeyMpttAdmin, NodeAdmin):
    # add to display ajax booleans and fkey_list links
    list_display = (
        'indented_short_title', 'item_link', 'node_link', 'id', 'slug', 'level',
        'toggle_active', 'toggle_menu_in', 'toggle_menu_in_chain',
        'toggle_menu_jump', 'toggle_menu_login', 'toggle_menu_current',
    )

    # mptt_tree ajax boolean
    toggle_active           = ajax_boolean('active', 'active?')
    toggle_menu_in          = ajax_boolean('menu_in', 'menu in?')
    toggle_menu_in_chain    = ajax_boolean('menu_in_chain', 'chain in?')
    toggle_menu_jump        = ajax_boolean('menu_jump', 'jump?')
    toggle_menu_login       = ajax_boolean('menu_login_required', 'login?')
    toggle_menu_current     = ajax_boolean('menu_show_current', 'h1 title?')

    # fkey_list links
    item_link = fkey_list_link('item', model_set='item_set',  fkey_name='node',   with_add_link=True)
    node_link = fkey_list_link('node', model_set='children',  fkey_name='parent', with_add_link=True)

    # mptt_tree indented title with fkey_list links
    def indented_short_title_text(self, item):
        return '%s %s' % (
            u'<a href="%s" title="show related elements">%s</a>' % (self.item_link(item, url_only='list'),  unicode(item),),
            u'<nobr>(<a href="%s/" title="edit &laquo;%s&raquo;">edit</a>)</nobr>' % (item.pk, item.__class__._meta.verbose_name,),
        )

class ItemNiceAdmin(AjaxBoolAdmin, FkeyListAdmin, ItemAdmin):
    # add to display ajax booleans and image_tag
    list_display = (
        'name', 'id', 'slug', 'sort', 'image_tag',
        'toggle_active', 'toggle_visible', 'toggle_show_item_name',
        'toggle_show_node_link', 'toggle_show_in_meta',
    )

    # add image field to first section
    fieldsets = copy.copy(ItemAdmin.fieldsets)
    fieldsets[0][1]['fields'] += ('image',)

    # mptt_tree ajax boolean
    toggle_active           = ajax_boolean('active', 'active?')
    toggle_visible          = ajax_boolean('visible', 'visible?')
    toggle_show_item_name   = ajax_boolean('show_item_name', 'name?')
    toggle_show_node_link   = ajax_boolean('show_node_link', 'to list?')
    toggle_show_in_meta     = ajax_boolean('show_in_meta', 'meta?')