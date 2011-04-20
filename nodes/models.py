from django.db import models
from django.utils.translation import ugettext_lazy as _
from sakkada.models.fields.imagefield import AdvancedImageWithThumbnailsField
from system.node_model import Node
from system.item_model import Item
import mptt

# -----------------------------------------------------------------------------
# Node Main 
class NodeMain(Node):
    node_name               = 'main'

    class Meta:
        verbose_name        = _('main node')
        verbose_name_plural = _('main nodes')
        ordering            = ['tree_id', 'lft']

class ItemMain(Item):
    node_name               = 'main'
    node                    = models.ForeignKey(NodeMain, help_text=_('Parent node.'), related_name='item_set')
    image                   = AdvancedImageWithThumbnailsField(
                                _('Image'), blank=True, null=True, upload_to="upload/nodes/main/images/item/%Y/%m/",
                                max_width=800, max_height=600, max_quality=90, clearable=True,
                                thumbnail={'size': (70, 70), 'options': ('crop', 'upscale'),},
                                extra_thumbnails={'main': {'size': (150, 150), 'options': ('crop', 'upscale')}},
                            )

    class Meta:
        verbose_name        = _('main item')
        verbose_name_plural = _('main items')
        ordering            = ['-date_start', '-sort']

    def image_tag(self):
        return self.image.thumbnail_tag if self.image else ''
    image_tag.short_description = _('Image')
    image_tag.allow_tags = True

class ItemImageMain(models.Model):
    node_name               = 'main'
    item                    = models.ForeignKey(ItemMain, help_text=_('Parent item.'), related_name='image_set')
    name                    = models.CharField(max_length=200, blank=True, null=True)
    sort                    = models.IntegerField(default=500)
    image                   = AdvancedImageWithThumbnailsField(
                                _('Image'), blank=True, upload_to="upload/nodes/main/images/itemimage/%Y/%m/",
                                max_width=800, max_height=600, max_quality=90, clearable=True,
                                thumbnail={'size': (70, 70), 'options': ('crop', 'upscale')},
                                extra_thumbnails={'main': {'size': (150, 150), 'options': ('crop', 'upscale')}},
                            )

    class Meta:
        verbose_name        = _('main item image')
        verbose_name_plural = _('main item images')
        ordering            = ['-sort']
        
    def image_tag(self):
        return self.image.thumbnail_tag if self.image else ''
    image_tag.short_description = _('Image')
    image_tag.allow_tags = True
        
# register all mptt classes
mptt.register(NodeMain)