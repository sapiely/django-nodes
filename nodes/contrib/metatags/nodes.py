from nodes.base import Modifier, Menu
from nodes.modifiers import MetaDataProcessor as BaseMetaDataProcessor
from .tags import MetaTags


# MetaData class mixin
class MetaTagsMetaDataMixin:
    metatags = None
    metatags_class = MetaTags

    def __init__(self):
        super().__init__()
        self.metatags = self.metatags_class()


# Modifier class mixin and mixed class
class MetaTagsMetaDataProcessorMixin(Modifier):
    def modify(self, request, data, meta, **kwargs):
        super().modify(request, data, meta, **kwargs)
        if request.nodes.selected:
            request.nodes.metatags = self.get_node_metatags(
                request.nodes.selected) + request.nodes.metatags

    def get_node_metatags(self, node):
        return (node.get_metatags() if hasattr(node, 'get_metatags') else
                node.data.get('metatags', None))


class MetaDataProcessor(MetaTagsMetaDataProcessorMixin,
                        BaseMetaDataProcessor):
    pass


# Menu class mixin
class MetaTagsMenuMixin(Menu):
    def get_data(self, obj):
        data = super().get_data(obj)
        data['metatags'] = (obj.get_metatags()
                            if hasattr(obj, 'get_metatags') else None)
        return data


# NavigationNode class mixin
class MetaTagsNavigationNodeMixin:
    def get_metatags(self):
        return self.data.get('metatags', None)
