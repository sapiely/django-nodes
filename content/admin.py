from django.contrib import admin
from django.conf import settings
from nodes.admin import NodeAdmin, ItemAdmin
from sakkada.admin.cache_clear import CacheClearAdmin
from sakkada.admin.editors.tinymce import EditorAdmin
from models import NodeMain, ItemMain, ItemImageMain

# Main node admin
class NodeMainAdmin(CacheClearAdmin, EditorAdmin, NodeAdmin):
    tinymce_fields = ['text']

class ItemImageMainInline(admin.TabularInline):
    model = ItemImageMain
    classes = ['collapse']
    extra = 3

class ItemMainAdmin(EditorAdmin, ItemAdmin):
    inlines = [ItemImageMainInline]
    tinymce_fields = ['descr', 'text']

admin.site.register(NodeMain, NodeMainAdmin)
admin.site.register(ItemMain, ItemMainAdmin)
admin.site.index_template = 'admin/cache/index_admin.html'