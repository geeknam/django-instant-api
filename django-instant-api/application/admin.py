from application import models
from django.contrib import admin

class ApplicationAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name')
    ordering = ('name',)
    list_display = ('name', 'verbose_name')
admin.site.register(models.Application, ApplicationAdmin)


class ModelFieldInline(admin.StackedInline):
    model = models.ModelField
    extra = 0

class ApplicationModelAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name')
    ordering = ('app','name')
    list_display = ('name', 'verbose_name', 'app')
    list_filter = ('app',)
    inlines = [
        ModelFieldInline,
    ]

admin.site.register(models.ApplicationModel, ApplicationModelAdmin)


class ModelFieldAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name', 'field_type')
    ordering = ('name',)
    list_display = ('name', 'verbose_name', 'model')
    list_filter = ('model',)

admin.site.register(models.AdminSetting, admin.ModelAdmin)
admin.site.register(models.ApiSerialiserSetting, admin.ModelAdmin)

for model in models.ApplicationModel.objects.all():
    admin.site.register(model.as_model(), model.as_admin())
