from django.db import models
from django.utils.translation import ugettext_lazy as _

class Item(models.Model):
    """A simple node's item model"""

    # fields start
    # data
    active                  = models.BooleanField(_("is active"), default=True)
    date_start              = models.DateTimeField(_("start date"), blank=True, null=True, db_index=True)
    date_end                = models.DateTimeField(_("end date"), blank=True, null=True, db_index=True)
    sort                    = models.IntegerField(_("sort"), default=500)
    name                    = models.CharField(_("name"), max_length=2000)
    descr                   = models.TextField(_("previev text"), max_length=20000, blank=True, null=True)
    text                    = models.TextField(_("detail text"), max_length=200000, blank=True, null=True)

    # path
    slug                    = models.SlugField(_("slug"), max_length=255, db_index=True)
    link                    = models.CharField(_("link"), max_length=255, db_index=True, blank=True, null=True)

    # seo
    meta_description        = models.TextField(_("meta description"), max_length=1000, blank=True, null=True)
    meta_keywords           = models.CharField(_("meta keywords"), max_length=255, blank=True, null=True)
    meta_title              = models.CharField(_("meta title"), max_length=255, blank=True, null=True, help_text=_("overwrite the title (html title tag)"))

    # stat info
    date_create             = models.DateTimeField(editable=False, auto_now_add=True)
    date_update             = models.DateTimeField(editable=False, auto_now=True)

    # behaviour
    template                = models.CharField(_("template"), max_length=100, null=True, blank=True, help_text=_('template to render the content instead original'))
    view                    = models.CharField(_("view"), max_length=100, null=True, blank=True, help_text=_('alternative view for item detail view'))
    visible                 = models.BooleanField(_("visible"), default=True, help_text=_('show item in items list, also redirect if alone'))
    show_item_name          = models.BooleanField(_("show item name"), default=True, help_text=_('show item name (usually in h2 tag)'))
    show_node_link          = models.BooleanField(_("show link to node"), default=True, help_text=_('show link to parent node'))
    show_in_meta            = models.BooleanField(_("show in meta"), default=True, help_text=_('show item name in meta title and chain'))
    # fields end

    class Meta:
        verbose_name        = _('item')
        verbose_name_plural = _('items')
        ordering = ['-date_start', '-sort']
        abstract = True

    def __unicode__(self):
        return self.name
        
    @models.permalink
    def get_absolute_url(self, path=None, node_link=False):
        path = path or (self.node.get_link_or_path())
        path = str(path.strip('/'))
        slug = '' if node_link else 'i/%s/' % self.slug
        
        kwargs = {'path':path, '_0':slug}
        self._cache_url_kwargs = kwargs
        
        return ('nodes_%s' % self.node_name, (), kwargs)
        
    def get_absolute_url_for_node(self, **kwargs):
        kwargs['node_link'] = True
        return self.get_absolute_url(**kwargs)

    @models.permalink
    def get_absolute_url_cache(self, node_link=False):
        kwargs = self._cache_url_kwargs if hasattr(self, '_cache_url_kwargs') and isinstance(self._cache_url_kwargs, dict) else None
        kwargs = kwargs or {'path':'cache/error_link/for/%s' % self.slug, '_0':''}
        kwargs['_0'] = '' if node_link else 'i/%s/' % self.slug
        return ('nodes_%s' % self.node_name, (), kwargs)

    def get_absolute_url_cache_for_node(self):
        return self.get_absolute_url_cache(node_link=True)
        
    def get_link_or_absolute_url(self, cache=False, **kwargs):
        if self.link:
            return self.link
        else:
            return self.get_absolute_url_cache(**kwargs) if cache else self.get_absolute_url(**kwargs)

    def get_link_or_absolute_url_cache(self):
        return self.get_link_or_absolute_url(cache=True)