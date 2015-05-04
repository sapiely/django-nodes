from django.utils.translation import ugettext_lazy as _
from django.db import models
from mptt.models import TreeManager, MPTTModel
from nodes.models import Node, Item


class NodeMain(MPTTModel, Node):
    node_name = 'main'
    objects = TreeManager()

    class Meta:
        verbose_name = _('main node')
        verbose_name_plural = _('main nodes')
        ordering = ('tree_id', 'lft',)


class ItemMain(Item):
    node_name = 'main'
    node = models.ForeignKey(NodeMain, help_text=_('Parent node.'),
                             related_name='item_set')

    class Meta:
        verbose_name = _('main item')
        verbose_name_plural = _('main items')
        ordering = ('-date_start', '-sort',)
