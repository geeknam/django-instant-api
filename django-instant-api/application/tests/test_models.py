from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from application import models


class ApplicationModelTestCase(TestCase):

    def setUp(self):
        self.app = models.Application.objects.create(
            name='tasks', verbose_name='Task'
        )

        self.model = models.ApplicationModel.objects.create(
            name='Task', verbose_name='Task',
            app=self.app
        )

        self.title_field = models.ModelField.objects.create(
            name='title', verbose_name='Title',
            model=self.model, field_type='application_charfield',
            null=True, blank=True
        )

    def tearDown(self):
        self.app.delete()

    def test_as_model(self):
        model = self.model.as_model()
        self.assertEqual(model.__name__, 'Task')
        self.assertIsNotNone(model._meta)
        self.assertEqual(model._meta.app_label, self.app.name)
        self.assertEqual(
            model._meta.verbose_name, self.app.verbose_name
        )
        self.assertEqual(
            model._meta.get_all_field_names(),
            ['id', 'title']
        )
        self.assertEqual(
            model._meta.get_field_by_name('title')[0].__class__.__name__,
            'CharField'
        )

    def test_as_admin(self):
        admin = self.model.as_admin()
        self.assertEqual(admin.__name__, 'TaskAdmin')



class ModelFieldTestcase(TestCase):

    def setUp(self):
        self.app = models.Application.objects.create(
            name='tasks', verbose_name='Task'
        )

        self.model = models.ApplicationModel.objects.create(
            name='Task', verbose_name='Task',
            app=self.app
        )

        self.title_field = models.ModelField.objects.create(
            name='title', verbose_name='Title',
            model=self.model, field_type='application_charfield',
            null=True, blank=True
        )

    def tearDown(self):
        self.app.delete()

    def test_field(self):
        field = self.title_field.as_field()
        self.assertTrue(field.null)
        self.assertTrue(field.blank)

    def test_field_as_fk(self):
        self.user_field = models.ModelField.objects.create(
            name='owner', verbose_name='Owner',
            model=self.model, field_type='user',
            null=True, blank=True
        )
        field = self.user_field.as_field()
        # Field is ForeignKey
        self.assertEqual(
            field.__class__.__name__, 'ForeignKey'
        )
        # Related model is User
        self.assertEqual(
            field.rel.to,
            ContentType.objects.get(model='user').model_class()
        )

    def test_field_as_app_model(self):
        self.account_model = models.ApplicationModel.objects.create(
            name='Account', verbose_name='Account',
            app=self.app
        )
        self.account_field = models.ModelField.objects.create(
            name='account', verbose_name='Account',
            model=self.model, field_type='account',
            null=True, blank=True
        )
        field = self.account_field.as_field()
        # Field is ForeignKey
        self.assertEqual(
            field.__class__.__name__,
            'ForeignKey'
        )
        # Related model is Account
        self.assertEqual(
            field.rel.to,
            models.ApplicationModel.objects.get(name='Account').as_model()
        )
