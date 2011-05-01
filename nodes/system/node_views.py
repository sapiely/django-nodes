from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.db.models import Q
from ..toolbox import class_by_name_and_type, jump_node_by_node, meta_to_request
from ..toolbox.pagination import pagination as pagination_tool
from ..toolbox.querystring import QueryString

class NodeView(TemplateView):
    node = None
    item = None
    queryset = None
    queryset_item = None
    options = {}
    classes = {}
    context_ex = {}

    def get(self, request, **kwargs):
        """get node data and call required view (node, list or item) or 404"""
        meta_to_request(request)

        # get models
        Node = class_by_name_and_type(self.kwargs['node_name'], 'node')
        Item = class_by_name_and_type(self.kwargs['node_name'], 'item')

        # get current node
        node = self.get_node(Node)

        # get node's options
        filter      = node.get_filter(Q(node=node.id, active=True))
        order_by    = node.get_order_by(['-date_start', '-sort'])

        # set instance data
        self.node = node
        self.options = {'filter': filter & Q(visible=True), 'filter_item': filter, 'order_by': order_by,}
        self.classes = {'node': Node, 'item': Item}
        self.queryset       = Item.objects.select_related('node').filter(self.options['filter']).order_by(*self.options['order_by'])
        self.queryset_item  = Item.objects.select_related('node').filter(self.options['filter_item'], slug=kwargs['item']) if kwargs['item'] else None

        context = self.behaviour()
        if issubclass(context.__class__, HttpResponse):
            return context

        context = self.get_context_data(**context)
        return self.render_to_response(context)

    def get_node(self, model):
        """get curent node"""
        path    = self.kwargs['path'].strip('/').split('/')
        filter  = Q(path='/'.join(path[:-1]))
        filter &= Q(slug=path[-1])
        filter |= Q(link='%s' % '/'.join(path))
        filter &= Q(active=True)

        # get node or 404
        node = get_object_or_404(model.objects.filter(filter))

        # if link is defined, access by path + slug is deined
        if node.link and node.link != '/'.join(path):
            raise Http404(u'Node field link [%s] defined, access by path [%s] denied.' % (node.link, '/'.join(path)))

        return node

    def behaviour(self):
        """main behaviour"""
        node = self.node

        # extra view
        if node.view:
            response = self.view_ex_by_name(node.view, 'node')
            if response:
                return response

        # main item behaviour
        # if slug - anyway show item
        if self.kwargs['item']:
            return self.view_item()

        # main node behaviour
        # menu jump
        node_to = node.menu_jump and jump_node_by_node(node)
        if node_to:
            return HttpResponseRedirect(node_to.get_absolute_url())

        node.items_count = self.queryset.count()

        # if zero count or "always node" > if node.text - node view, else 404
        if node.behaviour == 'node' or not node.items_count:
            if not node.text:
                raise Http404(u'No Items in node "%s" (behaviour: "%s").' % (node, node.behaviour))
            return self.view_node()

        # list view if conditions, else item view
        if node.behaviour == 'list' or (node.behaviour != 'item' and node.items_count>1):
            return self.view_list()
        else:
            return self.view_item()

    def view_node(self):
        """node self view"""
        template            = 'node.%s.html' % self.node.template if self.node.template else 'node.html'
        self.template_name  = ["nodes/%s/%s" % (self.node.node_name, template), "nodes/%s" % template]

        return {'node': self.node}

    def view_list(self):
        """node list of items view"""
        node    = self.node
        onpage  = node.onpage if 0 < node.onpage < 1000 else 10

        # paginator and page
        paginator   = Paginator(self.queryset, onpage)
        page        = self.request.GET.get('page', '1')
        page        = int(page) if page.isdigit() else 1
        try:
            item_list   = paginator.page(page)
        except (EmptyPage, InvalidPage):
            page        = paginator.num_pages
            item_list   = paginator.page(page)
        pagination  = pagination_tool(item_list, 2)
        # end paginator

        template            = 'list.%s.html' % node.template if node.template else 'list.html'
        self.template_name  = ["nodes/%s/%s" % (node.node_name, template), "nodes/%s" % template]

        context     = {
            'node':         node,
            'item_list':    item_list,
            'pagination':   pagination,
            'url_no_page':  node.get_absolute_url(),
            'query_string': QueryString(self.request),
        }

        return context

    def view_item(self):
        """node item's detail view"""
        queryset = self.queryset_item if self.kwargs['item'] else self.queryset[:1]

        # get item or 404
        self.item = item = get_object_or_404(queryset)

        # extended view
        if item.view:
            response = self.view_ex_by_name(item.view, 'item')
            if response:
                return response

        # storage meta data
        if item.show_in_meta:
            self.request.meta.chain.append({'link':self.request.get_full_path(), 'name':item.name})
            self.request.meta.title.append(item.meta_title or item.name)
            self.request.meta.keywords.append(item.meta_keywords)
            self.request.meta.description.append(item.meta_description)

        template            = 'item.%s.html' % (item.template or item.node.template) if item.template or item.node.template else 'item.html'
        self.template_name  = ["nodes/%s/%s" % (item.node_name, template), "nodes/%s" % template]

        context = {
            'item':         item,
            'query_string': QueryString(self.request),
        }

        return context

    def get_template_names(self):
        if not self.template_name or not isinstance(self.template_name, list):
            raise Exception(u'Node requires a definition of template_name as list or an implementation of get_template_names()')
        return self.template_name

    def get_context_data(self, **kwargs):
        context = kwargs
        context.update(self.context_ex)
        return context

    def view_ex_by_name(self, view_name, obj_type):
        """get extraview by name and type"""
        view_ex = 'extraview_%s_%s' % (obj_type, view_name)
        view_ex = getattr(self, view_ex, None)
        view_ex = view_ex if callable(view_ex) else None
        if not view_ex:
            raise Http404(u'Extra view "%s" for node "%s/%s(%s)" is not accessible.' % (self.node.view, self.node.node_name, self.node.slug, self.node.pk))
        response = view_ex(self.request, **self.kwargs)
        return response if issubclass(response.__class__, HttpResponse) else None