from django.contrib import admin
from sakkada.admin.editors.tinymce import EditorAdmin
from toolbox.admin import NodeNiceAdmin, ItemNiceAdmin
from models import NodeMain, ItemMain

# Main node admin
class NodeMainAdmin(EditorAdmin, NodeNiceAdmin):
    tinymce_fields = ['text']

class ItemMainAdmin(EditorAdmin, ItemNiceAdmin):
    tinymce_fields = ['descr', 'text']

admin.site.register(NodeMain, NodeMainAdmin)
admin.site.register(ItemMain, ItemMainAdmin)
admin.site.index_template = 'admin/cache/index_admin.html'