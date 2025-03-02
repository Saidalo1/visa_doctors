from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.i18n import set_language
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from root.settings import DEBUG, STATIC_ROOT, MEDIA_ROOT

urlpatterns = [
    # Language switcher
    path('i18n/setlang/', set_language, name='set_language'),
    
    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # CKEditor 5
    path("ckeditor5/", include('django_ckeditor_5.urls')),

    # Sentry debug
    path('sentry-debug/', lambda request: 1 / 0, name='test-sentry'),
]

# Translatable URLs
urlpatterns += i18n_patterns(
    # Admin panel
    path('admin/', admin.site.urls),

    # App URLs
    path('', include('app.urls')),
    
    prefix_default_language=True
)

if DEBUG:
    # Debug Toolbar
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]
    
    # Static and Media files
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': STATIC_ROOT}),
    ]
