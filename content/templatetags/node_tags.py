import re
from django import template
from django.apps import apps
from menus.template import inclusion_tag
from nodes.models import Node, Item


NAME_PATTERN = 'nodes/tags/%s.%s.html'
FREGEX = re.compile(r"""([a-z0-9_]+) \s*=\s* ("|')? (?(2) (?:(.+?)(?<!\\)\2) | ([^\s'"]+))""",
                    re.I | re.X)


def show_node(context, model=None, node_id=None, template=None,
              slices=None, filter=None, order_by=None, varname=None):
    """
    Shows the requested node and filtered children
    - model:    name of node model (example - NodeMain)
    - node_id:  id or slug of requested node
    - template: alternative template name, converts to
                "nodes/tags/node.{template or node_slug}.html"
                if value is False, do not render any template
    - slices:   slice object for items queryset
                (like real slice - "{from}:{to}:{step}")
    - filter:   params for filtering items (example: "attr=value attr2='v 2'"),
                default {'active': True,}
                Note that None, True, False and digist with no quotes
                will be converted to real python types,
                so
                    "aa=None bb='None' cc=123 dd='123'"
                converts to
                    {'aa': None, 'bb':'None', 'cc':123, 'dd':'123'}
    - order_by: ordering params (like original - "sort -id"),
                default "-date_start -sort"
    - varname:  alternative (to default name "object") name of context
                variable name

    If template is empty, tag will work like {% ... as varname %}
    (varname default is "object"), sometimes it is more usable,
    than render any templates.
    """
    request, model = context.get('request', None), nodes_model(model, Node)
    if not request or not model or not node_id:
        return {'template': None,}

    idfilter = {'pk' if isinstance(node_id, int) else 'slug': node_id,}
    try:
        node = model.objects.get(**idfilter)
    except model.DoesNotExist:
        return {'template': None,}

    slices = slices_parser(slices)
    filter = filter_parser(filter, node.item_set.model) or {'active': True,}
    order_by = order_by_parser(order_by, node.item_set.model) or ('-date_start', '-sort',)
    node.item_list = node.item_set.select_related('node').filter(**filter) \
                                  .order_by(*order_by)[slice(*slices)]

    template = (NAME_PATTERN % ('node', template or node.slug)
                if template else None)
    varname = varname or 'object'
    context.update({'template': template, varname: node,})
    return context

def show_item(context, model=None, item_id=None, template=None, varname=None):
    """
    Shows the requested item
    - model:    name of item model (example - ItemMain)
    - item_id:  id or slug of requested item
    - template: alternative template name, converts to
                "nodes/tags/item.{template or item_slug}.html",
                if value is False, do not render any template
    - varname:  alternative (to default name "object") name of
                context variable name

    If template is empty, tag will work like {% ... as varname %}
    (varname default is "object"), sometimes it is more usable,
    than render any templates.
    """
    request, model = context.get('request', None), nodes_model(model, Item)
    if not request or not model or not item_id:
        return {'template': False,}

    idfilter = {'pk' if isinstance(item_id, int) else 'slug': item_id,}
    try:
        item = model.objects.get(**idfilter)
    except model.DoesNotExist:
        return {'template': False,}

    template = (NAME_PATTERN % ('item', template or item.slug)
                if template else None)
    varname = varname or 'object'
    context.update({'template': template, varname: item,})
    return context

def filter_parser(filter, model):
    """Parse html like params into dict"""
    fields = [i.name for i in model._meta.fields]
    varval = lambda x: eval(x) if x in ('None', 'False', 'True') or x.isdigit() else x
    filter = re.findall(FREGEX, filter) if isinstance(filter, basestring) else []
    filter = [(str(i[0]), i[2] or varval(i[3])) \
              for i in filter if str(i[0]).split('__')[0] in fields]
    return dict(filter)

def order_by_parser(order_by, model):
    """Parse django queryset ordering params into list"""
    fields = [i.name for i in model._meta.fields]
    order_by = order_by if isinstance(order_by, basestring) else ''
    order_by = [i for i in order_by.split(' ') if i and i.replace('-', '', 1) in fields]
    return order_by

def slices_parser(slices):
    """Parse python slice params into list (tuple)"""
    slices = str(slices) if isinstance(slices, basestring) else ''
    try:
        slices = [int(i) if i else None for i in slices.split(':')[:3]]
    except ValueError, e:
        slices = (None,)
    return slices

def nodes_model(name, parent):
    """Get model by name and ancestor"""
    for i in models.get_models():
        if i.__name__ == name and issubclass(i, parent):
            return i

register = template.Library()
inclusion_tag_ex(register, takes_context=True)(show_node)
inclusion_tag_ex(register, takes_context=True)(show_item)
