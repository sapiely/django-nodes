from django.utils.translation import ugettext_lazy as _
from django.contrib import admin
from sakkada.admin.fkey_in import FkeyInMpttAdmin, fkey_in_link
from sakkada.admin.fein.tree_editor import TreeEditor
from sakkada.admin.fein.meta_editor import ajax_editable_boolean

class NodeAdmin(TreeEditor, FkeyInMpttAdmin, admin.ModelAdmin):
    list_display = (
        'name', 'id', 'slug', 'level',
        'toggle_active', 'toggle_menu_in', 'toggle_menu_in_chain', 'toggle_menu_jump', 'toggle_menu_login', 'toggle_menu_current', 
        'item_link', 'node_link', 
    )

    ordering = ['site', 'tree_id', 'lft']
    list_filter = ['level']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
            (None, {
                'fields': ('name', 'active', 'text')
            }),
            (_('path and relation settings'), {
                'classes': ('collapse',),
                'fields': ('slug', 'link', 'parent', 'site',)
            }),
            (_('menu settings'), {
                'classes': ('collapse',),
                'fields': ('menu_title', 'menu_extender', 'menu_in', 'menu_in_chain', 'menu_jump', 'menu_login_required', 'menu_show_current')
            }),
            (_('meta settings'), {
                'classes': ('collapse',),
                'fields': ('meta_title', 'meta_keywords', 'meta_description',)
            }),
            (_('behaviour settings'), {
                'classes': ('collapse',),
                'fields': ('behaviour', 'filter', 'filter_date', 'template', 'view', 'order_by', 'onpage')
            }),
        )

    toggle_active           = ajax_editable_boolean('active', 'active?')
    toggle_menu_in          = ajax_editable_boolean('menu_in', 'menu in?')
    toggle_menu_in_chain    = ajax_editable_boolean('menu_in_chain', 'chain in?')
    toggle_menu_jump        = ajax_editable_boolean('menu_jump', 'jump?')
    toggle_menu_login       = ajax_editable_boolean('menu_login_required', 'login?')
    toggle_menu_current     = ajax_editable_boolean('menu_show_current', 'h1 title?')
    
    item_link = fkey_in_link('item', model_set='item_set',  fkey_name='node',   with_add_link=True)
    node_link = fkey_in_link('node', model_set='children',  fkey_name='parent', with_add_link=True)

    def get_form(self, request, obj=None, **kwargs):
        form = super(NodeAdmin, self).get_form(request, obj=None, **kwargs)
        # indent tree node titles
        form.base_fields['parent'].label_from_instance = lambda obj: u'%s %s' % ('. ' * obj.level, obj)
        return form