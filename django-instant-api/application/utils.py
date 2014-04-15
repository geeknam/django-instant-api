from django.utils.importlib import import_module
from django.contrib.contenttypes.models import ContentType
from django.db import models

import inspect

def get_field_map():
    field_map = {}
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and name.endswith('Field'):
            application_field = 'application_%s' %  name.lower()
            field_map[application_field] = ('django.db.models', name)
    return field_map


def get_module_attr(module, attr, fallback=None):
    m = import_module(module)
    return getattr(m, attr, fallback)


def get_field_choices():
    django_fields = []
    django_fields.append(
        ('Basic Fields', [(key, value[1]) for key, value in get_field_map().items()])
    )
    curlabel = None
    curmodels = None
    try:
        for c in ContentType.objects.all().order_by('app_label'):
            if c.app_label != curlabel:
                if curlabel is not None:
                    django_fields.append((curlabel.capitalize(), curmodels))
                curlabel = c.app_label
                curmodels = []
            curmodels.append((c.model, c.name.capitalize()))
        django_fields.append((curlabel.capitalize(), curmodels))
    except Exception as e:
        # ContentTypes aren't available yet, maybe pre-syncdb
        print e
        pass

    return django_fields


def get_unicode(self):
    unival = []
    for f in self._meta.fields:
        if len(unival) < 3 and f.__class__ is models.CharField:
            unival.append(getattr(self, f.name))
    if len(unival) > 0:
        return u' '.join(unival)
    else:
        return self.verbose_name