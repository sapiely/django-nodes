import re
from django import template
from nodes.base import registry
from nodes.utils.template import inclusion_tag, get_from_context


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


register = template.Library()
load_menu = register.tag(load_menu)
inclusion_tag(register, takes_context=True)(show_menu)
