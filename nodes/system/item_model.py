from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

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
        
    def get_absolute_url(self, use_link=True):
        if use_link and self.link:
            link = self.link
        else:
            data = {'path': self.node.get_link_or_path().strip('/').__str__(), '_0': 'i/%s/' % self.slug}
            link = reverse('nodes_%s' % self.node_name, kwargs=data)
        return link
        
    def get_absolute_url_real(self):
        return self.get_absolute_url(use_link=False)