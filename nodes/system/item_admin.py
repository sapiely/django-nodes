from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib import admin
from sakkada.admin.fkey_in import FkeyInAdmin, fkey_in_link
from sakkada.admin.fein.list_editor import ListEditor
from sakkada.admin.fein.meta_editor import ajax_editable_boolean

class ItemAdmin(ListEditor, FkeyInAdmin, admin.ModelAdmin):
    list_display = (
        'name', 'id', 'slug', 'image_tag',
        'toggle_active', 'toggle_visible', 'toggle_show_item_name', 'toggle_show_node_link', 'toggle_show_in_meta', 
    )

    ordering = ['-sort']
    list_filter = ['node', 'date_create']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
            (None, {
                'fields': ('active', 'date_start', 'date_end', 'name', 'sort', 'descr', 'text', 'image')
            }),
            (_('path and node settings'), {
                'classes': ('collapse',),
                'fields': ('slug', 'link', 'node',)
            }),
            (_('meta settings'), {
                'classes': ('collapse',),
                'fields': ('meta_title', 'meta_keywords', 'meta_description',)
            }),
            (_('behaviour settings'), {
                'classes': ('collapse',),
                'fields': ('template', 'view', 'visible', 'show_item_name', 'show_node_link', 'show_in_meta',)
            }),
        )
    
    toggle_active           = ajax_editable_boolean('active', 'active?')
    toggle_visible          = ajax_editable_boolean('visible', 'visible?')
    toggle_show_item_name   = ajax_editable_boolean('show_item_name', 'name?')
    toggle_show_node_link   = ajax_editable_boolean('show_node_link', 'to list?')
    toggle_show_in_meta     = ajax_editable_boolean('show_in_meta', 'meta?')

    def get_form(self, request, obj=None, **kwargs):
        form = super(ItemAdmin, self).get_form(request, obj=None, **kwargs)
        # indent tree node titles
        form.base_fields['node'].label_from_instance = lambda obj: u'%s %s' % ('. ' * obj.level, obj)
        return form