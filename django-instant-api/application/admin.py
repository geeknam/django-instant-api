from application.models import Application, ApplicationModel, AdminSetting, ApiSerialiserSetting, ModelField
from django.contrib import admin

class ApplicationAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name')
    ordering = ('name',)
    list_display = ('name', 'verbose_name')
admin.site.register(Application, ApplicationAdmin)


class ModelFieldInline(admin.TabularInline):
    model = ModelField
    extra=10


class ApplicationModelAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name')
    ordering = ('app','name')
    list_display = ('name', 'verbose_name', 'app')
    list_filter = ('app',)
    inlines = [ModelFieldInline]

admin.site.register(ApplicationModel, ApplicationModelAdmin)


class ModelFieldAdmin(admin.ModelAdmin):
    search_fields = ('name','verbose_name', 'field_type')
    ordering = ('name',)
    list_display = ('name', 'verbose_name', 'model')
    list_filter = ('model',)

admin.site.register(AdminSetting, admin.ModelAdmin)
admin.site.register(ApiSerialiserSetting, admin.ModelAdmin)

for model in ApplicationModel.objects.all():
    admin.site.register(model.as_model(), model.as_admin())
