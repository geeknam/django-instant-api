from django.db.models import get_model
from rest_framework import serializers, viewsets
from import_export.admin import ImportExportModelAdmin


class AdminMixin(object):

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


class ApiMixin(object):

    @property
    def default_serialiser(self):
        attrs = {}
        class Meta:
            model = self.as_model()
        attrs['Meta'] = Meta
        serializer_name = '%sSerializer' % self.name.capitalize()
        return type(str(serializer_name), (serializers.HyperlinkedModelSerializer,), attrs)

    def get_related_serialisers(self):
        fks = [
            field for field in self.as_model()._meta.fields
            if field.__class__.__name__.split('.')[-1] == 'ForeignKey'
        ]
        related_serialisers = {}
        for fk in fks:
            try:
                ApplicationModel = get_model('application', 'ApplicationModel')
                app_model = ApplicationModel.objects.get(
                    name__iexact=fk.rel.to._meta.model_name)
                related_serialisers[fk.rel.to._meta.model_name] = app_model.as_api_serialiser()()
            except ApplicationModel.DoesNotExist:
                pass
        return related_serialisers

    def as_api_serialiser(self):
        attrs = {}
        if self.api_serialiser:
            if self.api_serialiser.nested:
                attrs.update(self.get_related_serialisers())
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
            'serializer_class': self.default_serialiser,
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
