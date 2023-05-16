from django import template
from django.utils.safestring import mark_safe
from django.utils.text import smart_split
from django.template.base import kwarg_re
from nodes.base import registry
from nodes.utils.template import (inclusion_tag_function, get_from_context,
                                  BlockTagFunction, BlockTagNode)


# Menus template tags
# -------------------
def show_menu(context, from_level=0, to_level=100,
              extra_inactive=0, extra_active=100,
              template=None, show_invisible=False, show_inactive_branch=False,
              menuconf=None, modifiers=None, extra_active_mode=0, **kwargs):
    """
    render a nested list of all children of the pages
    - from_level: starting level
    - to_level: max level
    - extra_inactive: how many levels should be rendered of the not active tree?
    - extra_active: how deep should the children of the active node be rendered?
    - template: template used to render the menu
    - show_invisible: show nodes marked as hidden
    - show_inactive_branch: show nodes in inactive branch (use when from_level > 0)
    - menuconf: menuconf name, usually retrieve implicitly by routing
    - modifiers: modifiers group name (see settings file) or direct value of list
    """

    # set template by default
    template = template or "menus/menu.html"
    # if there's an exception (500), default context_processors may not be called.
    request = context.get('request', None)
    if not request:
        return {'template': None,}

    kwargs.update(cut_levels={
        'from_level': from_level,
        'to_level': to_level,
        'extra_inactive': extra_inactive,
        'extra_active': extra_active,
        'extra_active_mode': extra_active_mode,
        'show_invisible': show_invisible,
        'show_inactive_branch': show_inactive_branch,
    })

    # get result nodes tree
    menuconf = registry.processor.menuconf(request, name=menuconf)
    nodes = registry.processor.get_nodes(menuconf, request,
                                         modifiers=modifiers, **kwargs)
    if not nodes:
        return {'template': None,}

    context.update({
        'children': nodes['nodes'],
        'selected': nodes['selected'],
        'template': template,
        'menuconf': menuconf,
        'kwargs': kwargs,
    })
    return context


def load_menu(parser, token):
    """loads menu, set data to request.meta first"""
    class LoadMenuNode(template.Node):
        def render(self, context):
            request = get_from_context(context, 'request')
            registry.processor.get_nodes(None, request, init_only=True)
            return ''
    return LoadMenuNode()


# Meta information showing tags
# -----------------------------
def show_meta_title(context, main_title='', template='metas/title.html',
                    check_context=True):
    """
    Render a meta title tag string.
    - main_title: title of the first title's segment
    - template: template used to render the title tag
    - check_context: append title by metadata:title context variable
    """
    request = get_from_context(context, 'request')
    title_meta_tag = request.nodes.metatags.data.get('title', None)
    title = ([main_title] if main_title else [])
    if title_meta_tag is not None:
        title += [request.nodes.metatags.data.pop('title').data.get('value')]
    else:
        title += request.nodes.title
    metadata = context.get('metadata', None)
    if isinstance(metadata, dict) and check_context:
        title += [str(i) for i in metadata.get('title', [])]
    context.update({'title': title, 'template': template, })
    return context


def show_meta_chain(context, main_title='', main_url='/', start_level=0,
                    template="metas/chain.html", check_context=True):
    """
    Shows the breadcrumbs according to the current request.
    - main_title: title of the first breadcrumb
                  (if empty, will be ignored together with main_url)
    - main_url: url of the first breadcrumb, used if main_title (see below)
    - start_level: after which level should the breadcrumbs start? (0 == home)
    - template: template used to render the breadcrumbs
    - check_context: append chain by metadata:chain context variable
    """
    request = get_from_context(context, 'request')
    chain = ([{'name': main_title, 'link': main_url,}]
             if main_title else []) + request.nodes.chain
    metadata = context.get('metadata', None)
    if isinstance(metadata, dict) and check_context:
        chain = chain + metadata.get('chain', [])
    context.update({'chain': chain.items[start_level:], 'template': template,})
    return context


def show_meta_selected(context, pattern="<h1>%s</h1>"):
    """Shows the selected node name (main header of the page)."""
    request = get_from_context(context, 'request')
    selected = request.nodes.selected
    pattern = pattern if '%s' in pattern else '%s'
    pattern = (pattern % selected.data.get('title', selected.title)
               if selected and selected.data.get('show_meta_selected', True)
               else '')
    metadata = context.get('metadata', None)
    print(metadata)
    print(isinstance(metadata, dict))
    if isinstance(metadata, dict):
        try:
            pattern = metadata.get('title', [])[0].title
            print(pattern)
        except Exception:
            pass
    return mark_safe(pattern)


# Meta information setting tags
# -----------------------------
def set_meta_title(context, value, action='add'):
    """Set new meta title item value."""
    request = get_from_context(context, 'request')
    addleft = action == 'addleft'
    value = [str(value)] if str(value) else None
    if value:
        request.nodes.title = (value + request.nodes.title if addleft else
                               request.nodes.title + value)
    return ''


def set_meta_chain(context, value, url=None, action='add', **kwargs):
    """Set new meta chain item value."""
    request = get_from_context(context, 'request')
    addleft = action == 'addleft'
    if url:
        value = {
            'title': str(value), 'url': url,
            'data': {k[5:]: v for k, v in kwargs.items()
                     if k.startswith('data_')},
        }
    if value:
        request.nodes.chain = (value + request.nodes.chain if addleft else
                               request.nodes.chain + value)
    return ''


class SetMetaTitleNode(BlockTagNode):
    cache_prefix = 'metatitle'

    def render(self, context):
        request = context.get('request', None)
        if not request:
            return ''

        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)

        addleft = resolved_kwargs.get('action', 'add') == 'addleft'
        cache_key, cache_timeout = self.get_cache_kwargs(resolved_kwargs)

        title = None
        if cache_key:
            title = cache.get(cache_key, None)

        if not title:
            title = self.nodelist.render(context).strip().splitlines()
            title = [i for i in map(str.strip, title) if i]

        if title and cache_key:
            cache.set(cache_key, title, cache_timeout)

        if self.target_var:
            context[self.target_var] = title
        else:
            request.nodes.title = (title + request.nodes.title if addleft else
                                   request.nodes.title + title)
        return ''


class SetMetaChainNode(BlockTagNode):
    cache_prefix = 'metachain'
    default_delimiter = '---'

    def get_chain_from_text(self, text, delimiter=None):
        chain = [[]]
        lines = [i for i in map(str.strip, text.strip().splitlines()) if i]
        delimiter = delimiter or self.default_delimiter
        for i in lines:
            chain[-1].append(i) if not i == delimiter else chain.append([])

        return [{'title': i[0], 'url': i[1],
                 'data': self.get_attrs(i[2]) if len(i)>2 else {},}
                for i in chain if 2 <= len(i) <= 3]

    def get_attrs(self, value):
        attrs = [kwarg_re.match(i) for i in smart_split(value)]
        attrs = [i.groups() for i in attrs if i.group(1) is not None]
        return dict(attrs) if attrs else {}

    def render(self, context):
        request = context.get('request', None)
        if not request:
            return ''

        resolved_args, resolved_kwargs = self.get_resolved_arguments(context)

        addleft = resolved_kwargs.get('action', 'add') == 'addleft'
        delimiter = resolved_kwargs.get('delimiter', self.default_delimiter)
        cache_key, cache_timeout = self.get_cache_kwargs(resolved_kwargs)

        chain = None
        if cache_key:
            chain = cache.get(cache_key, None)

        if not chain:
            chain = self.get_chain_from_text(self.nodelist.render(context),
                                             delimiter=delimiter)

        if chain and cache_key:
            cache.set(cache_key, chain, cache_timeout)

        if self.target_var:
            context[self.target_var] = chain
        else:
            request.nodes.chain = (chain + request.nodes.chain if addleft else
                                   request.nodes.chain + chain)
        return ''


# Template tags functions
# -----------------------
show_menu_inclusion_tag_function = inclusion_tag_function(
    show_menu, takes_context=True)
show_meta_title_inclusion_tag_function = inclusion_tag_function(
    show_meta_title, takes_context=True)
show_meta_chain_inclusion_tag_function = inclusion_tag_function(
    show_meta_chain, takes_context=True)

set_meta_title_block = BlockTagFunction(
    tag_name='set_meta_title_block', function_name='set_meta_title_function',
    takes_context=True, template_node_class=SetMetaTitleNode)
set_meta_chain_block = BlockTagFunction(
    tag_name='set_meta_chain_block', function_name='set_meta_chain_function',
    takes_context=True, template_node_class=SetMetaChainNode)


register = template.Library()
register.tag(load_menu)
register.tag(show_menu_inclusion_tag_function)

register.tag(show_meta_title_inclusion_tag_function)
register.tag(show_meta_chain_inclusion_tag_function)
register.simple_tag(takes_context=True)(show_meta_selected)

register.tag(set_meta_title_block)
register.tag(set_meta_chain_block)
register.simple_tag(takes_context=True)(set_meta_title)
register.simple_tag(takes_context=True)(set_meta_chain)
