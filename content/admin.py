from django.contrib import admin
from nodes.admin import NodeAdmin, ItemAdmin
from sakkada.admin.editors.tinymce import EditorAdmin
from models import NodeMain, ItemMain, ItemImageMain

# Main node admin
class NodeMainAdmin(EditorAdmin, NodeAdmin):
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