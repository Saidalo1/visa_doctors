from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from root.settings import DEBUG, STATIC_ROOT, MEDIA_ROOT, STATIC_URL, MEDIA_URL


urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # CKEditor 5
    path("ckeditor5/", include('django_ckeditor_5.urls')),

    # Sentry debug
    path('sentry-debug/', lambda request: 1 / 0, name='test-sentry'),
]

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
