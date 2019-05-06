from django import template
from django.db import models
from django.core.cache import cache
from django.utils.safestring import mark_safe
from nodes.utils.template import (get_from_context,
                                  BlockTagFunction, BlockTagNode)
from ..tags import MetaTags
from ..utils import get_metatags_for_object


def show_meta_tags(context, check_context=True):
    """
    Shows all current request realted metatags.
    - check_context: append metatags by metadata:metatags context variable
    """
    request = get_from_context(context, 'request')
    metadata = context.get('metadata', None)
    metatags = request.nodes.metatags
    if isinstance(metadata, dict) and check_context:
        metatags = metatags + metadata.get('metatags', None)
    return mark_safe(metatags)


# Metatags information setting tags
# ---------------------------------
class MetaTagsNode(BlockTagNode):
    cache_prefix = 'metatags'

    def render(self, context):
        request = context.get('request', None)
        if not request:
            return ''

        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)

        action = resolved_kwargs.get('action', 'add')
        render = resolved_kwargs.get('render', False)
        check_context = resolved_kwargs.get('check_context', True)
        cache_key, cache_timeout = self.get_cache_kwargs(resolved_kwargs)

        metatags = None
        if cache_key:
            metatags = cache.get(cache_key, None)

        if not metatags:
            metatags = MetaTags(action=action)
            metatags.set(self.nodelist.render(context))

        if metatags and cache_key:
            cache.set(cache_key, metatags, cache_timeout)

        if self.target_var:
            context[self.target_var] = metatags
            return ''
        else:
            request.nodes.metatags += metatags

        return show_meta_tags(context,
                              check_context=check_context) if render else ''


def set_meta_tags(context, value, action='add'):
    request = get_from_context(context, 'request')

    if isinstance(value, models.Model):
        value = get_metatags_for_object(value)
    elif not isinstance(value, MetaTags):
        value = MetaTags(value, action=action)

    request.nodes.metatags += value
    return ''


# Template tags functions
# -----------------------
set_meta_tags_block = BlockTagFunction(
    tag_name='set_meta_tags_block', function_name='set_meta_tags_function',
    takes_context=True, template_node_class=MetaTagsNode)


register = template.Library()
register.simple_tag(takes_context=True)(show_meta_tags)

register.tag(set_meta_tags_block)
register.simple_tag(takes_context=True)(set_meta_tags)
