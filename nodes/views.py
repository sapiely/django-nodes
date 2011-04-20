from django.db import models
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from toolbox import node_class_by_name, views_ex_by_name, jump_node_by_node, meta_to_request
from toolbox.pagination import pagination as pagination_tool
from toolbox.querystring import QueryString

def main(request, **kwargs):
    """main node view"""
    meta_to_request(request)
    
    slug    = kwargs['item']
    path    = kwargs['path'].strip('/').split('/')
    filter  = models.Q(path='/'.join(path[:-1]))
    filter &= models.Q(slug=path[-1])
    filter |= models.Q(link='%s' % '/'.join(path))
    filter &= models.Q(active=True)

    # get models
    Node = node_class_by_name(kwargs['node_name'], 'node')
    Item = node_class_by_name(kwargs['node_name'], 'item')

    # get node or 404
    node = get_object_or_404(Node.objects.filter(filter))

    # if link is defined, access by path + slug is deined
    if node.link and node.link != '/'.join(path):
        raise Http404('Node field link [%s] defined, access by path [%s] denied.' % (node.link, '/'.join(path)))

    options         = node.get_filter(models.Q(node=node.id, active=True))
    options         = {'filter_item': options, 'filter': options & models.Q(visible=True), 'order_by': node.get_order_by(['-date_start', '-sort']),}
    queryset        = Item.objects.select_related('node').filter(options['filter']).order_by(*options['order_by'])
    queryset_item   = Item.objects.select_related('node').filter(options['filter_item'], slug=slug) if slug else None
    kwparams        = {'node': node, 'queryset': queryset, 'queryset_item': queryset_item, 'kwargs': kwargs, 'options': options, 'classes': {'node':Node, 'item':Item}, 'context_ex':{}}

    # extended view
    if node.view:
        views_ex = views_ex_by_name(node.view, node.node_name, 'node')
        if not views_ex:
            raise Http404(u'View extra "%s" for node "%s" is not accessble.' % (node.view, node.node_name))
        kwparams = views_ex(request, **kwparams)
        if issubclass(kwparams.__class__, HttpResponse):
            return kwparams

    # main item behaviour
    # if slug - anyway show item
    if slug:
        return main_item(request, **kwparams)

    # main node behaviour
    # menu jump
    node_to = node.menu_jump and jump_node_by_node(node)
    if node_to:
        return HttpResponseRedirect(node_to.get_absolute_url())

    # if zero count or "always node" > if node.text - node view, else 404
    count = queryset.count()
    if (node.behaviour == 'node' or not count) and node.text:
        return main_node(request, **kwparams)
    elif (node.behaviour == 'node' or not count):
        raise Http404(u'No Items in node "%s" (behaviour: "%s").' % (node, node.behaviour))

    # list view if conditions, else item view
    if node.behaviour == 'list' or (node.behaviour != 'item' and count>1):
        return main_list(request, **kwparams)
    else:
        return main_item(request, **kwparams)

def main_node(request, **kwargs):
    """node self view"""

    node        = kwargs['node']

    template    = 'node.%s.html' % node.template if node.template else 'node.html'
    templates   = ["nodes/%s/%s" % (node.node_name, template), "nodes/%s" % template]

    context     = {'node': node}
    context.update(kwargs['context_ex'])

    return render_to_response(templates, context, context_instance=RequestContext(request))

def main_list(request, **kwargs):
    """node list of items view"""

    node        = kwargs['node']
    queryset    = kwargs['queryset']
    onpage      = node.onpage if 0 < node.onpage < 1000 else 10

    # paginator and page
    paginator   = Paginator(queryset, onpage)
    page        = request.GET.get('page', '1')
    page        = int(page) if page.isdigit() else 1
    try:
        item_list   = paginator.page(page)
    except (EmptyPage, InvalidPage):
        page        = paginator.num_pages
        item_list   = paginator.page(page)
    pagination  = pagination_tool(item_list, 2)
    # end paginator

    template    = 'list.%s.html' % node.template if node.template else 'list.html'
    templates   = ["nodes/%s/%s" % (node.node_name, template), "nodes/%s" % template]

    context     = {
        'node':         node,
        'item_list':    item_list,
        'pagination':   pagination,
        'url_no_page':  node.get_absolute_url(),
        'query_string': QueryString(request),
    }
    context.update(kwargs['context_ex'])

    return render_to_response(templates, context, context_instance=RequestContext(request))

def main_item(request, **kwargs):
    """node item's detail view"""

    queryset = kwargs['queryset_item'] if kwargs['kwargs']['item'] else kwargs['queryset'][0:1]

    # get item or 404
    item = get_object_or_404(queryset)

    # extended view
    if item.view:
        views_ex = views_ex_by_name(item.view, item.node_name, 'item')
        if not views_ex:
            raise Http404(u'View extra "%s" for item in node "%s" is not accessble.' % (item.view, item.node_name))
        kwparams = views_ex(request, item, **kwargs)
        if issubclass(kwparams.__class__, HttpResponse):
            return kwparams
        item, kwargs = kwparams

    # storage meta data
    if item.show_in_meta:
        request.meta.chain.append({'link':request.get_full_path(), 'name':item.name})
        request.meta.title.append(item.meta_title or item.name)
        request.meta.keywords.append(item.meta_keywords)
        request.meta.description.append(item.meta_description)

    template    = 'item.%s.html' % (item.template or item.node.template) if item.template or item.node.template else 'item.html'
    templates   = ["nodes/%s/%s" % (item.node_name, template), "nodes/%s" % template]

    context     = {
        'item':         item,
        'query_string': QueryString(request),
    }
    context.update(kwargs['context_ex'])

    return render_to_response(templates, context, context_instance=RequestContext(request))