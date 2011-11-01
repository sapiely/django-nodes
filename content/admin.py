from django.contrib import admin
from sakkada.admin.editors.tinymce import EditorAdmin
from toolbox.admin import NodeNiceAdmin, ItemNiceAdmin
from models import NodeMain, ItemMain, ItemImageMain

# Main node admin
class NodeMainAdmin(EditorAdmin, NodeNiceAdmin):
    tinymce_fields = ['text']

class ItemImageMainInline(admin.TabularInline):
    model = ItemImageMain
    classes = ['collapse']
    extra = 3

class ItemMainAdmin(EditorAdmin, ItemNiceAdmin):
    inlines = [ItemImageMainInline]
    tinymce_fields = ['descr', 'text']

admin.site.register(NodeMain, NodeMainAdmin)
admin.site.register(ItemMain, ItemMainAdmin)
admin.site.index_template = 'admin/cache/index_admin.html'