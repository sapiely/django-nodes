from django.contrib import admin
from system.node_admin import NodeAdmin
from system.item_admin import ItemAdmin
from models import NodeMain, ItemMain, ItemImageMain
from sakkada.admin.editors.tinymce import EditorAdmin

# -----------------------------------------------------------------------------
# Main admin

# Node main admin
class NodeMainAdmin(EditorAdmin, NodeAdmin):
    tinymce_fields = ['text']

# Item main admin
class ItemImageMainInline(admin.TabularInline):
    model = ItemImageMain
    extra = 3
    classes = ['collapse']

class ItemMainAdmin(EditorAdmin, ItemAdmin):
    inlines = [ItemImageMainInline]
    tinymce_fields = ['descr', 'text']

admin.site.register(NodeMain, NodeMainAdmin)
admin.site.register(ItemMain, ItemMainAdmin)