import inspect
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.db import router
from django.db.models.loading import cache
from django.utils.datastructures import SortedDict
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers, viewsets
from import_export.admin import ImportExportModelAdmin

from application import actions, utils


def get_field_map():
    field_map = {}
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and name.endswith('Field'):
            application_field = 'application_%s' %  name.lower()
            field_map[application_field] = ('django.db.models', name)
    return field_map


DJANGO_FIELD_CHOICES = [
    ('Basic Fields', [(key, value[1]) for key, value in get_field_map().items()])
]
def get_field_choices():
    del DJANGO_FIELD_CHOICES[:]
    DJANGO_FIELD_CHOICES.append(
        ('Basic Fields', [(key, value[1]) for key, value in get_field_map().items()])
    )
    curlabel = None
    curmodels = None
    try:
        for c in ContentType.objects.all().order_by('app_label'):
            if c.app_label != curlabel:
                if curlabel is not None:
                    DJANGO_FIELD_CHOICES.append((curlabel.capitalize(), curmodels))
                curlabel = c.app_label
                curmodels = []
            curmodels.append((c.model, c.name.capitalize()))
        DJANGO_FIELD_CHOICES.append((curlabel.capitalize(), curmodels))
    except:
        # ContentTypes aren't available yet, maybe pre-syncdb
        print "WARNING: ContentType is not availble"
        pass

    return DJANGO_FIELD_CHOICES

class Application(models.Model):

    class Meta:
        verbose_name = _('Application')

    name = models.SlugField(
        verbose_name=_('Application Name'),
        help_text=_('Internal name for this application. Lower case, plural'),
        max_length=255, unique=True,
        null=False, blank=False
    )
    verbose_name = models.CharField(
        verbose_name=_('Verbose Name'),
        help_text=_('Display name for this application'),
        max_length=255, null=False, blank=False
    )

    def __unicode__(self):
        return self.verbose_name

class ApplicationModel(models.Model):

    class Meta:
        verbose_name = _('Model')
        unique_together = (('app', 'name'),)

    name = models.SlugField(
        verbose_name=_('Model Name'),
        help_text=_('Internal name for this model'),
        max_length=64, null=False, blank=False
    )

    verbose_name = models.CharField(
        verbose_name=_('Verbose Name'),
        help_text=_('Display name for this model'),
        max_length=128, null=False, blank=False
    )

    app = models.ForeignKey(
        'application.Application',
        related_name='models',null=False, blank=False
    )

    def uncache(self):
        '''
        Removes the model this instance represents from Django's cache

        We need to remove the model from the cache whenever we change it
        otherwise it won't have the changes next time it's loaded
        '''

        cached_models = cache.app_models.get(self.app.name, SortedDict())
        if cached_models.has_key(self.name.lower()):
            del cached_models[self.name.lower()]

    def as_model(self):
        attrs = {}
        class Meta:
            app_label = self.app.name
            verbose_name = self.verbose_name
        attrs['Meta'] = Meta
        attrs['__module__'] = 'applications.%s.models' % self.app.name
        def uni(self):
            unival = []
            for f in self._meta.fields:
                if len(unival) < 3 and f.__class__ is models.CharField:
                    unival.append(getattr(self, f.name))
            if len(unival) > 0:
                return u' '.join(unival)
            else:
                return self.verbose_name
        attrs['__unicode__'] = uni
        for field in self.fields.all():
            attrs[field.name] = field.as_field()
        return type(str(self.name), (models.Model,), attrs)

    def as_admin(self):
        attrs = {}
        admin_name = '%sAdmin' % self.name.capitalize()
        return type(str(admin_name), (ImportExportModelAdmin,), attrs)

    def as_serializer(self):
        attrs = {}
        class Meta:
            model = self.as_model()
        attrs['Meta'] = Meta
        serializer_name = '%sSerializer' % self.name.capitalize()
        return type(str(serializer_name), (serializers.HyperlinkedModelSerializer,), attrs)

    def as_view_set(self):
        attrs = {
            'queryset': self.as_model().objects.all(),
            'serializer_class': self.as_serializer(),
            'paginate': 50
        }
        viewset_name = '%sViewSet' % self.name.capitalize()
        return type(str(viewset_name), (viewsets.ModelViewSet,), attrs)

    def save(self, force_insert=False, force_update=False, using=None):
        using = using or router.db_for_write(self.__class__, instance=self)
        create = False
        if self.pk is None or not self.__class__.objects.filter(pk=self.pk).exists():
            create = True
        super(ApplicationModel, self).save(force_insert, force_update, using)
        if create:
            actions.create(self.as_model(), using)
        _update_dynamic_field_choices()
        self.uncache()

    def __unicode__(self):
        return self.verbose_name

class ModelField(models.Model):

    class Meta:
        verbose_name = _('Model Field')
        unique_together = (('model', 'name'),)
        ordering = ('id',)

    name = models.SlugField(
        verbose_name=_('Field Name'),
        help_text=_('Internal name for this field'),
        max_length=64, null=False, blank=False
    )

    verbose_name = models.CharField(
        verbose_name=_('Verbose Name'),
        help_text=_('Display name for this field'),
        max_length=128, null=False, blank=False
    )

    model = models.ForeignKey(
        'application.ApplicationModel', related_name='fields',
        null=False, blank=False
    )

    field_type = models.CharField(
        verbose_name=_('Field Type'),
        help_text=_('Field Data Type'),
        choices=get_field_choices(),
        max_length=128, null=False, blank=False
    )

    null = models.BooleanField(
        verbose_name=_('Null'),
        help_text=_('Can this field contain null values?'),
        default=True, null=False, blank=False
    )

    blank = models.BooleanField(
        verbose_name=_('Blank'),
        help_text=_('Can this field contain empty values?'),
        default=True, null=False, blank=False
    )

    unique = models.BooleanField(
        verbose_name=_('Unique'),
        help_text=_('Restrict this field to unique values'),
        default=False, null=False, blank=False
    )

    default = models.CharField(
        verbose_name=_('Default value'),
       help_text=_('Default value given to this field when none is provided'),
       max_length=32, null=True, blank=True
    )

    help_text = models.CharField(
        verbose_name=_('Help Text'),
        help_text=_('Short description of the field\' purpose'),
        max_length=256, null=True, blank=True
    )

    def as_field(self):
        attrs = {
            'verbose_name': self.verbose_name,
            'null': self.null,
            'blank': self.blank,
            'unique': self.unique,
            'help_text': self.help_text,
        }

        not_unique = [
            'application_imagefield'
        ]
        if self.field_type in not_unique:
            attrs.pop('unique')

        if self.default is not None and self.default != '':
            attrs['default'] = self.default

        field_class = None
        if self.field_type in get_field_map():
            module, klass = get_field_map()[self.field_type]
            field_class = utils.get_module_attr(module, klass, models.CharField)

        if field_class is None:
            try:
                ctype = ContentType.objects.get(model=self.field_type)
                field_class = models.ForeignKey
                model_def = ApplicationModel.objects.get(name__iexact=ctype.model, app__name__iexact=ctype.app_label)
                model_klass = model_def.as_model()
                attrs['to'] = model_klass
                if attrs['to'] is None:
                    del attrs['to']
                    raise Exception('Could not get model class from %s' % ctype.model)
            except Exception, e:
                print "Failed to set foreign key: %s" % e
                field_class = None

        if field_class is None:
            print "No field class found for %s, using CharField as default" % self.field_type
            field_class = models.CharField

        if field_class is models.CharField:
            attrs['max_length'] = 255

        return field_class(**attrs)

    def delete(self, using=None):
        from south.db import db
        model_class = self.model.as_model()
        table = model_class._meta.db_table
        db.delete_column(table, self.name)

        super(ModelField, self).delete(using)
        self.model.uncache()

    def save(self, force_insert=False, force_update=False, using=None):
        from south.db import db
        create = False
        if self.pk is None or not self.__class__.objects.filter(pk=self.pk).exists():
            create = True

        model_class = self.model.as_model()
        field = self.as_field()
        table = model_class._meta.db_table
        if create:
            db.add_column(table, self.name, field, keep_default=False)
        else:
            pass#db.alter_column(table, self.name, field)

        super(ModelField, self).save(force_insert, force_update, using)
        self.model.uncache()

    def __unicode__(self):
        return self.verbose_name

def _update_dynamic_field_choices():
    ModelField._meta.get_field_by_name('field_type')[0]._choices = get_field_choices()
