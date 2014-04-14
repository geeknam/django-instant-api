from django.conf.urls import patterns, include, url
from django.contrib import admin

from rest_framework import routers
from application.models import ApplicationModel

admin.autodiscover()


router = routers.DefaultRouter()
for model in ApplicationModel.objects.all():
    router.register(model.verbose_name_plural.lower(), model.as_view_set())


urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'django_instant_api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(router.urls)),
)
