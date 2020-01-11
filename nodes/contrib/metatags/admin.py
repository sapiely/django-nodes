from django import forms
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.forms.widgets import Media, Textarea
from django.contrib.contenttypes.forms import BaseGenericInlineFormSet
from django.contrib.contenttypes.admin import (GenericTabularInline,
                                               GenericStackedInline)
from .models import BaseMetaTag, BaseMetaTagsContainer, MetaTagsMixin
from .tags import registry, MetaTagValueError
from .utils import get_metatags_model, get_metatags_container_for_object


# Admin forms
# -----------
class MetaTagTextarea(Textarea):
    metatag_editor_use_in_admin = True

    def __init__(self, attrs=None):
        attrs = attrs or {}
        cls = ' '.join([attrs.get('class', ''), 'editor_metatag']).strip()
        attrs = {'rows': 1, 'cols': 60, 'class': cls, **attrs}
        return super().__init__(attrs=attrs)

    @property
    def media(self):
        js = tuple()
        if self.metatag_editor_use_in_admin:
            js = '' if settings.DEBUG else '.min'
            js = ('admin/js/vendor/jquery/jquery%s.js' % js,
                  'admin/js/jquery.init.js',)
        js += (
            'admin/js/vendor/jquery/jquery.adjustable-field.js',
            'admin/metatags/metatag_editor.js',
        )
        return getattr(super(), 'media', Media()) + Media(js=js)


class BaseMetaTagForm(forms.ModelForm):
    name = forms.ChoiceField(label=_('name'), choices=(('', '---------',),))

    class Meta:
        fields = ('name', 'text', 'action',)
        widgets = {
            'text': MetaTagTextarea(attrs={
                'style': 'width: 95%; min-width: 30em;',
            }),
        }

    def clean(self):
        name = self.cleaned_data.get('name')
        text = self.cleaned_data.get('text')
        if name and text:
            try:
                message = None
                orig_name, self.instance.name = self.instance.name, name
                orig_text, self.instance.text = self.instance.text, text
                metatags = self.instance.get_metatag()
            except KeyError as e:
                message = "Key %s does not exists, you only 'obj' key." % e
            except IndexError as e:
                message = "You should use only named values {name}, not {}"
            except MetaTagValueError as e:
                message = str(e)
            except Exception as e:
                message = "Exception: %s" % e
            finally:
                self.instance.name = orig_name
                self.instance.text = orig_text
            if message is not None:
                raise forms.ValidationError({'text': message,})
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].choices += [(k, '{} ({})'.format(k, v.data_type),)
                                        for k, v in registry.data.items()]


class BaseMetaTagGenericInlineFormSet(BaseGenericInlineFormSet):

    def __init__(self, **kwargs):
        self.instance_original = instance = kwargs.get('instance', None)
        if isinstance(instance, MetaTagsMixin):
            self.instance_is_container = True
        else:
            self.instance_is_container = False
            instance = instance and get_metatags_container_for_object(instance)
        super().__init__(**{**kwargs, 'instance': instance,})

    def clean(self):
        if any(self.errors):
            return

        data = [i.cleaned_data for i in self.forms if i.cleaned_data]
        tags = [i['name'] for i in data]

        if not len(set(tags)) == len(tags):
            raise forms.ValidationError('Each tag should be defined only once.')

        # todo: allow to choose - generate container on the fly or
        #                         require it existance
        if not self.instance_is_container and not (self.instance and
                                                   self.instance.pk) and tags:
            raise forms.ValidationError('Metatags container is not defined.')


class MetaTagsContainerGenericInlineForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        action_field = self.fields['metatags_action']
        action_field.initial = ''
        action_field.choices = [('', '---------',),] + action_field.choices


# Admin classes
# -------------
class MetaTagGenericInline(GenericTabularInline):
    model = get_metatags_model(model='metatag') or BaseMetaTag
    fields = ('name', 'text', 'action',)
    form = BaseMetaTagForm
    formset = BaseMetaTagGenericInlineFormSet
    show_change_link = True
    can_delete = True
    min_num = 0
    max_num = 99
    extra = 0


class MetaTagsContainerGenericInline(GenericStackedInline):
    model = get_metatags_model(model='container') or BaseMetaTagsContainer
    fields = ('metatags_action',)
    form = MetaTagsContainerGenericInlineForm
    show_change_link = True
    can_delete = True
    min_num = 0
    max_num = 1
    extra = 0


class MetaTagAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'id', 'action',
        'content_type', 'object_id', 'content_object',)
    form = BaseMetaTagForm


class MetaTagsContainerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'metatags_action',
        'content_type', 'object_id', 'content_object',)
    inlines = (MetaTagGenericInline,)
