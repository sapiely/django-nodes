from django.utils.translation import ugettext_lazy as _
from django.db import models
from nodes.models import Node, Item
import mptt

# Main node models
class NodeMain(Node):
    node_name               = 'main'

    class Meta:
        verbose_name        = _('main node')
        verbose_name_plural = _('main nodes')
        ordering            = ['tree_id', 'lft']

class ItemMain(Item):
    node_name               = 'main'
    node                    = models.ForeignKey(NodeMain, help_text=_('Parent node.'),
                                                related_name='item_set')

    class Meta:
        verbose_name        = _('main item')
        verbose_name_plural = _('main items')
        ordering            = ['-date_start', '-sort']

# register mptt classes
mptt.register(NodeMain)