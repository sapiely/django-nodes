from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


class Node(models.Model):
    """A simple hierarchical node model"""

    CHOICES_BEHAVIOUR = (
        ('list', _('always list')),
        ('item', _('always item')),
        ('node', _('always node')),
    )

    CHOICES_FILTER = (
        ('date_req', 'required date_start'),
    )

    CHOICES_FILTER_DATE = (
        ('date_actual',         'actual (date_start < date)'),
        ('date_actual_both',    'actual (date_start < date < date_end)'),
        ('date_anounce',        'anounce (date < date_start)'),
    )

    FILTER_HANDLER = {
        'date_req':             lambda q: q & models.Q(date_start__isnull=False),
        'date_actual':          lambda q: q & models.Q(models.Q(date_start__lte=timezone.now()) | models.Q(date_start__isnull=True)),
        'date_actual_both':     lambda q: q & models.Q(models.Q(date_start__lte=timezone.now()) | models.Q(date_start__isnull=True),\
                                                       models.Q(date_end__gte=timezone.now()) | models.Q(date_end__isnull=True)),
        'date_anounce':         lambda q: q & models.Q(date_start__gte=timezone.now()),
    }

    # fields start
    # data
    name                = models.CharField(_("name"), max_length=2000)
    text                = models.TextField(_("detail text"), max_length=200000, blank=True)

    active              = models.BooleanField(_("is active"), default=True)
    login_required      = models.BooleanField(_("login required"), default=False)

    # path
    slug                = models.SlugField(_("slug"), max_length=255, db_index=True)
    path                = models.CharField(_("path"), max_length=255, db_index=True, blank=True, editable=False)
    link                = models.CharField(_("link"), max_length=255, db_index=True, blank=True, help_text=_("overwrite the path to this node (if leading slashes ('/some/url/') - node is only link in menu, else ('some/url') - standart behaviour)"))

    # seo
    meta_description    = models.TextField(_("meta description"), max_length=1000, blank=True)
    meta_keywords       = models.CharField(_("meta keywords"), max_length=255, blank=True)
    meta_title          = models.CharField(_("meta title"), max_length=255, blank=True, help_text=_("overwrite the title (html title tag)"))

    # relations
    site                = models.ForeignKey(Site, help_text=_('the site the page is accessible at.'), verbose_name=_("site"), default=1)
    parent              = models.ForeignKey('self', null=True, blank=True, related_name='children', verbose_name=_("node"), db_index=True)

    # stat info
    date_create         = models.DateTimeField(editable=False, auto_now_add=True)
    date_update         = models.DateTimeField(editable=False, auto_now=True)

    # behaviour
    behaviour           = models.CharField(_("list behaviour"), max_length=20, choices=CHOICES_BEHAVIOUR,   blank=True)
    filter              = models.CharField(_("filter"),         max_length=20, choices=CHOICES_FILTER,      blank=True)
    filter_date         = models.CharField(_("filter_date"),    max_length=20, choices=CHOICES_FILTER_DATE, blank=True)

    template            = models.CharField(_("template"), max_length=100, blank=True, help_text=_('the template used to render the content instead original'))
    view                = models.CharField(_("view"), max_length=100, blank=True, help_text=_('the view loaded instead original'))
    order_by            = models.CharField(_("ordering"), max_length=100, blank=True, help_text=_('overwrite default ordering (default is empty, equal to -date_start -sort, separate strongly with one space char)<br>possible keys: date_start, date_end, sort, name, slug, link'))
    onpage              = models.PositiveSmallIntegerField(_("onpage"), default=10, help_text=_('perpage count (default=10, 1<=count<=999)'))

    # menu
    menu_title          = models.CharField(_("menu title"), max_length=255, blank=True, help_text=_("overwrite the title in the menu"))
    menu_extender       = models.CharField(_("attached menu"), max_length=80, db_index=True, blank=True, help_text=_("menu extender"))
    menu_in             = models.BooleanField(_("in navigation"), default=True, db_index=True, help_text=_("this node in navigation (menu in?)"))
    menu_in_chain       = models.BooleanField(_("in chain and title"), default=True, db_index=True, help_text=_("this node in chain and title (chain in?)"))
    menu_jump           = models.BooleanField(_("jump to first child"), default=False, help_text=_("jump to the first child element if exist (jump?)"))
    menu_login_required = models.BooleanField(_("menu login required"), default=False, help_text=_("show this page in the menu only if the user is logged in (login?)"))
    menu_show_current   = models.BooleanField(_("show node name"), default=True, help_text=_('show node name in h1 tag if current (h1 title?)'))

    # tree
    level               = models.PositiveIntegerField(db_index=True, editable=False)
    lft                 = models.PositiveIntegerField(db_index=True, editable=False)
    rght                = models.PositiveIntegerField(db_index=True, editable=False)
    tree_id             = models.PositiveIntegerField(db_index=True, editable=False)
    # fields end

    class Meta:
        verbose_name        = _('node')
        verbose_name_plural = _('nodes')
        ordering = ['tree_id', 'lft']
        abstract = True

    def __unicode__(self):
        return self.name

    def save(self, is_moved=False, *args, **kwargs):
        """Update path variable"""
        is_create = self.pk is None
        # check slug modification
        if not (is_moved or is_create):
            original = self.__class__.objects.get(pk=self.pk)
            is_moved = (self.slug != original.slug) or (self.parent_id != original.parent_id)
        # get path value
        if is_moved or is_create:
            self.path = self.parent.get_path().strip('/') if self.parent else ''
        super(Node, self).save(*args, **kwargs)
        # cascade children path updating
        if is_moved:
            for item in self.children.all():
                item.save(is_moved=True)

    def get_filter(self, filter=None):
        node_f  = self.filter      and self.FILTER_HANDLER.get(self.filter, None)
        node_fd = self.filter_date and self.FILTER_HANDLER.get(self.filter_date, None)
        filter  = models.Q() if filter is None else filter
        filter  = node_f(filter)  if callable(node_f)  else filter
        filter  = node_fd(filter) if callable(node_fd) else filter
        return filter

    def get_order_by(self, default=None):
        fields      = [i.name for i in self.item_set.model._meta.fields]
        order_by    = [i for i in self.order_by.split(' ') if i.replace('-', '', 1) in fields] if self.order_by else []
        order_by    = order_by or default
        return order_by

    def get_path(self):
        return ('%s/' % self.path if self.path else '') + self.slug

    def get_link_or_path(self):
        return self.link.strip('/') if self.link else self.get_path()

    def get_absolute_url(self):
        if self.link and (self.link.startswith('/') or ('://' in self.link and self.link[0:self.link.index('://')].isalpha())):
            return self.link
        path = self.link or self.get_path()
        path = path.strip('/')
        return reverse('nodes_%s' % self.node_name, kwargs={'path':path})

    def get_menu_title(self):
        return self.menu_title or self.name

class Item(models.Model):
    """A simple node's item model"""

    # fields start
    # data
    active              = models.BooleanField(_("is active"), default=True)
    date_start          = models.DateTimeField(_("start date"), blank=True, null=True, db_index=True)
    date_end            = models.DateTimeField(_("end date"), blank=True, null=True, db_index=True)
    sort                = models.IntegerField(_("sort"), default=500)
    name                = models.CharField(_("name"), max_length=2000)
    descr               = models.TextField(_("preview text"), max_length=20000, blank=True)
    text                = models.TextField(_("detail text"), max_length=200000, blank=True)

    # path
    slug                = models.SlugField(_("slug"), max_length=255, db_index=True)
    link                = models.CharField(_("link"), max_length=255, db_index=True, blank=True)

    # seo
    meta_description    = models.TextField(_("meta description"), max_length=1000, blank=True)
    meta_keywords       = models.CharField(_("meta keywords"), max_length=255, blank=True)
    meta_title          = models.CharField(_("meta title"), max_length=255, blank=True, help_text=_("overwrite the title (html title tag)"))

    # stat info
    date_create         = models.DateTimeField(editable=False, auto_now_add=True)
    date_update         = models.DateTimeField(editable=False, auto_now=True)

    # behaviour
    template            = models.CharField(_("template"), max_length=100, blank=True, help_text=_('template to render the content instead original'))
    view                = models.CharField(_("view"), max_length=100, blank=True, help_text=_('alternative view for item detail view'))
    visible             = models.BooleanField(_("visible"), default=True, help_text=_('show item in items list, also redirect if alone (visible?)'))
    show_item_name      = models.BooleanField(_("show item name"), default=True, help_text=_('show item name, usually in h2 tag (name?)'))
    show_node_link      = models.BooleanField(_("show link to node"), default=True, help_text=_('show link to parent node (to list?)'))
    show_in_meta        = models.BooleanField(_("show in meta"), default=True, help_text=_('show item name in meta title and chain (meta?)'))
    # fields end

    class Meta:
        verbose_name        = _('item')
        verbose_name_plural = _('items')
        ordering = ['-date_start', '-sort']
        abstract = True

    def __unicode__(self):
        return self.name

    def get_absolute_url(self, use_link=True):
        if use_link and self.link:
            link = self.link
        else:
            data = {'path': self.node.get_link_or_path().strip('/').__str__(), '_0': 'i/%s/' % self.slug}
            link = reverse('nodes_%s' % self.node_name, kwargs=data)
        return link

    def get_absolute_url_real(self):
        return self.get_absolute_url(use_link=False)
