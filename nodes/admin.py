from django.contrib import admin
from system.node_admin import NodeAdmin
from system.item_admin import ItemAdmin
from sakkada.admin.editors.tinymce import EditorAdmin
from models import NodeMain, ItemMain, ItemImageMain

# -----------------------------------------------------------------------------
# Main admin

# Node main admin
class NodeMainAdmin(EditorAdmin, NodeAdmin):
    tinymce_fields = ['text']

# Item main admin
class ItemImageMainInline(admin.TabularInline):
    model = ItemImageMain
    classes = ['collapse']
    extra = 3

class ItemMainAdmin(EditorAdmin, ItemAdmin):
    inlines = [ItemImageMainInline]
    tinymce_fields = ['descr', 'text']

admin.site.register(NodeMain, NodeMainAdmin)
admin.site.register(ItemMain, ItemMainAdmin)