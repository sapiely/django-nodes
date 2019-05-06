from django.apps import AppConfig
from nodes import settings
from .tags import registry


class MetaTagsConfig(AppConfig):
    name = 'nodes.contrib.metatags'

    def ready(self):
        if settings.METATAGS:
            for name, cls in settings.METATAGS.items():
                registry.register_tag(name, cls)
