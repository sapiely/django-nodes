from django.apps import apps as djangoapps
from django.core.exceptions import ImproperlyConfigured
from nodes import settings as msettings
from .models import MetaTagsMixin


def get_metatags_model(model='metatag', as_string=False, silent=False):
    """MetaTag/MetaTagsContainer model getter active for this project."""
    if model not in ('metatag', 'container',):
        raise ValueError(
            'get_metatags_model can handle only "metatag" or "container"')

    try:
        setting = ('METATAGS_METATAG_MODEL' if model == 'metatag' else
                   'METATAGS_CONTAINER_MODEL')
        model = getattr(msettings, setting)
        if as_string or model is None:
            return model
        else:
            return djangoapps.get_model(model, require_ready=False)
    except AttributeError:
        msg = 'MENUS_%s must be defined for use contrib app models.' % setting
    except ValueError:
        msg = "MENUS_%s must be of the form 'app_label.ModelName'." % setting
    except LookupError:
        msg = "MENUS_%s refers to '%s' that has not been installed." % (
            setting, model)

    if not silent:
        raise ImproperlyConfigured(msg)


def get_metatags_container_for_object(obj):
    if isinstance(obj, MetaTagsMixin):
        return obj

    ContainerModel = get_metatags_model('container', silent=True)
    return ContainerModel and ContainerModel.get_for_object(obj)


def get_metatags_for_object(obj):
    container = get_metatags_container_for_object(obj)
    return container and container.get_metatags()
