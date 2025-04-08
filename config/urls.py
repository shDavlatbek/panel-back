from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from config.swagger import SwaggerUIView

# Swagger schema view configuration


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('web.urls')),
    
    path('swagger/', SwaggerUIView.with_ui(cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', SwaggerUIView.without_ui(cache_timeout=0), name='schema-json'),
]

# Add static/media file serving in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)