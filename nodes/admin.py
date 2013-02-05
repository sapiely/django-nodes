from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.contrib import admin
from django.db import models
from django import forms

class NodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'slug', 'level',)
    list_display_links = ('id',)
    list_filter = ('level',)

    ordering = ('site', 'tree_id', 'lft',)
    prepopulated_fields = {'slug': ('name',)}
    wideinput_fields = ('name', 'slug', 'link', 'menu_title', 'menu_extender',
                        'meta_title', 'meta_keywords', 'template', 'view', 'order_by',)
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
            'fields': ('menu_title', 'menu_extender', 'menu_in', 'menu_in_chain',
                       'menu_jump', 'menu_login_required', 'menu_show_current')
        }),
        (_('meta settings'), {
            'classes': ('collapse',),
            'fields': ('meta_title', 'meta_keywords', 'meta_description',)
        }),
        (_('behaviour settings'), {
            'classes': ('collapse',),
            'fields': ('behaviour', 'filter', 'filter_date', 'template',
                       'view', 'order_by', 'onpage')
        }),
    )

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(NodeAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        # change widget for wideinput_fields directly (not formfield_overrides)
        if hasattr(self, 'wideinput_fields') and db_field.name in self.wideinput_fields:
            formfield.widget = forms.TextInput(attrs={'maxlength': db_field.max_length,
                                                      'size': 100,})
        return formfield

    def get_form(self, request, obj=None, **kwargs):
        form = super(NodeAdmin, self).get_form(request, obj=None, **kwargs)
        # indent tree node titles
        form.base_fields['parent'].label_from_instance = lambda obj: u'%s %s' % \
                                                                     ('. ' * obj.level, obj)
        return form

class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'id', 'slug', 'sort',)
    list_filter = ('node', 'date_create',)

    ordering = ('-sort',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}
    wideinput_fields = ('name', 'slug', 'link', 'meta_title', 'meta_keywords',
                        'template', 'view',)
    fieldsets = (
            (None, {
                'fields': ('active', 'date_start', 'date_end', 'name', 'sort',
                           'descr', 'text',)
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
                'fields': ('template', 'view', 'visible', 'show_item_name',
                           'show_node_link', 'show_in_meta',)
            }),
        )

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(ItemAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        # change widget for wideinput_fields directly (not formfield_overrides)
        if hasattr(self, 'wideinput_fields') and db_field.name in self.wideinput_fields:
            formfield.widget = forms.TextInput(attrs={'maxlength': db_field.max_length,
                                                      'size': 100,})
        return formfield

    def get_form(self, request, obj=None, **kwargs):
        form = super(ItemAdmin, self).get_form(request, obj=None, **kwargs)
        # indent tree node titles
        form.base_fields['node'].label_from_instance = lambda obj: u'%s %s' % \
                                                                   ('. ' * obj.level, obj)
        return form