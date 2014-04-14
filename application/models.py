from django.db import models
from django.db import router
from django.db.models.loading import cache
from django.utils.datastructures import SortedDict
from django.contrib.contenttypes.models import ContentType

from rest_framework import serializers, viewsets
from import_export.admin import ImportExportModelAdmin

from application import actions, utils
from application.utils import get_field_map, get_field_choices, get_unicode


class Application(models.Model):

    class Meta:
        verbose_name = 'Application'

    name = models.SlugField(
        help_text='Internal name for this application. Lower case, plural',
        max_length=255, unique=True,
        null=False, blank=False
    )
    verbose_name = models.CharField(
        help_text='Display name for this application',
        max_length=255, null=False, blank=False
    )

    def __unicode__(self):
        return self.verbose_name


class ApplicationModel(models.Model):

    class Meta:
        verbose_name = 'Model'
        unique_together = (
            ('app', 'name'),
        )

    name = models.SlugField(
        help_text='Internal name for this model',
        max_length=64, null=False, blank=False
    )

    verbose_name = models.CharField(
        help_text='Display name for this model',
        max_length=128, null=False, blank=False
    )

    verbose_name_plural = models.CharField(
        help_text='Display plural name for this model',
        max_length=128, null=True, blank=True
    )

    app = models.ForeignKey('application.Application',
        related_name='models',
        null=False, blank=False
    )

    admin = models.OneToOneField(
        'application.AdminSetting',
        null=True, blank=True
    )

    api_serialiser = models.OneToOneField(
        'application.ApiSerialiserSetting',
        null=True, blank=True
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
            verbose_name_plural = self.verbose_name_plural or self.verbose_name + 's'
        attrs['Meta'] = Meta
        attrs['__module__'] = 'applications.%s.models' % self.app.name
        attrs['__unicode__'] = get_unicode
        for field in self.fields.all():
            attrs[field.name] = field.as_field()
        return type(str(self.name), (models.Model,), attrs)

    def as_admin(self):
        attrs = {}
        if self.admin:
            field_names = [field.name for field in self.admin._meta.fields]
            field_names.remove('id')
            for field_name in field_names:
                attr = getattr(self.admin, field_name)
                if attr:
                    attrs[field_name] = attr.split(',')
        admin_name = '%sAdmin' % self.name.capitalize()
        return type(str(admin_name), (ImportExportModelAdmin,), attrs)

    def as_serializer(self):
        attrs = {}
        class Meta:
            model = self.as_model()
        attrs['Meta'] = Meta
        serializer_name = '%sSerializer' % self.name.capitalize()
        return type(str(serializer_name), (serializers.HyperlinkedModelSerializer,), attrs)

    def as_api_serialiser(self):
        attrs = {}
        if self.api_serialiser:
            class Meta:
                model = self.as_model()
                fields = self.api_serialiser.fields.split(',')
            attrs['Meta'] = Meta
            serializer_name = '%sApiSerializer' % self.name.capitalize()
            return type(str(serializer_name), (serializers.ModelSerializer,), attrs)
        return

    def as_view_set(self):
        attrs = {
            'queryset': self.as_model().objects.all(),
            'serializer_class': self.as_serializer(),
            'paginate': 50,
        }
        if self.api_serialiser:
            attrs.update({
                'filter_fields': self.api_serialiser.filter_fields.split(',')
            })
        api_serialiser = self.as_api_serialiser()
        if api_serialiser:
            attrs['serializer_class'] = api_serialiser
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


class AdminSetting(models.Model):
    list_filter = models.CharField(max_length=255, null=True, blank=True)
    list_display = models.CharField(max_length=255, null=True, blank=True)
    search_fields = models.CharField(max_length=255, null=True, blank=True)

    def __unicode__(self):
        if hasattr(self, 'applicationmodel'):
            return u'%s.%sAdmin' % (
                self.applicationmodel.app.name,
                self.applicationmodel.name.capitalize()
            )
        return u'Settings'

class ApiSerialiserSetting(models.Model):
    fields = models.CharField(max_length=255)
    filter_fields = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'API settings'

    def __unicode__(self):
        if hasattr(self, 'applicationmodel'):
            return u'%s.%sSerialiser' % (
                self.applicationmodel.app.name,
                self.applicationmodel.name.capitalize()
            )
        return u'API Serialiser'

class ModelField(models.Model):

    class Meta:
        unique_together = (
            ('model', 'name'),
        )
        ordering = ('id',)

    name = models.SlugField(
        help_text='Internal name for this field',
        max_length=64, null=False, blank=False
    )

    verbose_name = models.CharField(
        help_text='Display name for this field',
        max_length=128, null=False, blank=False
    )

    model = models.ForeignKey('application.ApplicationModel',
        related_name='fields',
        null=False, blank=False
    )

    field_type = models.CharField(
        help_text='Field Data Type',
        choices=get_field_choices(),
        max_length=128, null=False, blank=False
    )

    null = models.BooleanField(
        help_text='Can this field contain null values?',
        default=True, null=False, blank=False
    )

    blank = models.BooleanField(
        help_text='Can this field contain empty values?',
        default=True, null=False, blank=False
    )

    unique = models.BooleanField(
        help_text='Restrict this field to unique values',
        default=False, null=False, blank=False
    )

    default = models.CharField(
       help_text='Default value given to this field when none is provided',
       max_length=32, null=True, blank=True
    )

    help_text = models.CharField(
        help_text='Short description of the field',
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
                try:
                    model_def = ApplicationModel.objects.get(name__iexact=ctype.model, app__name__iexact=ctype.app_label)
                    model_klass = model_def.as_model()
                except ApplicationModel.DoesNotExist:
                    model_klass = ctype.model_class()
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
