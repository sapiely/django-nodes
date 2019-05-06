from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from django.core import checks
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.fields import GenericRelation
from nodes import settings as msettings
from .tags import registry, MetaTags


METATAG_FIELD_HELP_TEXT = (
    'string: "value with spaces" attr=value attr2="value with spaces"'
    '<br>comma-separated: value, with, commas, and spaces'
    '<br>list: "value with spaces" attr=value'
    '<br>list: another one value'
    '<br>dict: foo:bar = value'
    '<br>dict: foo:baz = another one value'
)

ACTION_CHOICES = (
    ('set', _('Set (dismiss parent value)'),),
    ('unset', _('Unset (erase parent value)'),),
    ('add', _('Add (update parent value)'),),
    ('addleft', _('Addleft (update by parent value)'),),
)


class BaseMetaTag(models.Model):
    content_type = models.ForeignKey(
        ContentType, blank=False, null=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(default=0)
    content_object = GenericForeignKey('content_type', 'object_id')

    name = models.CharField(_('name'), max_length=128)
    text = models.TextField(
        _('text'), max_length=1024*32, blank=True,
        help_text=METATAG_FIELD_HELP_TEXT)
    plain = models.TextField(_('plain'), max_length=1024*32, blank=True)
    action = models.CharField(
        _('action'), max_length=32, choices=ACTION_CHOICES, default='add')

    class Meta:
        abstract = True
        unique_together = (('content_type', 'object_id', 'name',),)

    def __str__(self):
        return 'MetaTag "%s" action:%s for %s #%s: "%s"' % (
            self.name, self.action, self.content_type,
            self.object_id, self.content_object)

    def save(self, *args, **kwargs):
        self.plain = self.get_metatag().as_plain()
        super().save(*args, **kwargs)

    def get_metatag(self):
        cls = registry.get_tag(self.name)
        tag = cls.from_form(self.name, self.get_text(), self.action)
        return tag

    def get_content_object(self):
        obj = self.content_object
        if isinstance(obj, BaseMetaTagsContainer):
            obj = obj.content_object
        return obj

    def get_text(self, text=None):
        return (text or self.text or '').format(super='{super}',
                                                obj=self.get_content_object())


class MetaTagsMixin(models.Model):
    if msettings.METATAGS_METATAG_MODEL:
        metatags = GenericRelation(msettings.METATAGS_METATAG_MODEL)

    metatags_action = models.CharField(
        _('action'), max_length=32, choices=ACTION_CHOICES, default='add')

    class Meta:
        abstract = True

    def get_metatags(self):
        mt = MetaTags(action=self.metatags_action)
        mt.set(i.get_metatag() for i in self.metatags.all())
        return mt

    @classmethod
    def check(cls, **kwargs):
        return super().check(**kwargs) + cls._check_metatags_field()

    @classmethod
    def _check_metatags_field(cls):
        errors = []
        if not cls._meta.abstract:
            try:
                field = cls._meta.get_field('metatags')
                if (not isinstance(field, GenericRelation) or
                        not (issubclass(field.related_model, BaseMetaTag))):
                    raise FieldDoesNotExist
            except FieldDoesNotExist:
                errors.append(
                    checks.Error(
                        'MetaTagsMixin mixed model has no metatags'
                        ' GenericRelation field.',
                        hint='Set metatags = GenericRelation(MetaTagModel)'
                             ' field on {} model or set'
                             " MENUS_METATAGS_METATAG_MODEL = 'app_label.ModelName'"
                             ' value in settings.'.format(cls.__name__),
                        id='nodes.E010',
                        obj=cls,
                    )
                )

        return errors


class BaseMetaTagsContainer(MetaTagsMixin, models.Model):
    content_type = models.ForeignKey(
        ContentType, blank=False, null=True, on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(default=0)
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        abstract = True
        unique_together = (('content_type', 'object_id',),)

    def __str__(self):
        return 'MetaTags #%s for %s #%s: "%s"' % (
            self.id, self.content_type, self.object_id, self.content_object)

    @classmethod
    def get_for_object(cls, obj):
        ct = ContentType.objects.get_for_model(type(obj))
        return cls.objects.filter(content_type=ct, object_id=obj.id).first()

    @classmethod
    def get_metatags_for_object(cls, obj):
        container = cls.get_for_object(obj)
        return container and container.get_metatags()
