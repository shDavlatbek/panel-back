from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.renderers import SwaggerUIRenderer
from rest_framework import permissions
from drf_yasg.renderers import SwaggerYAMLRenderer, SwaggerJSONRenderer, OpenAPIRenderer


SchemaView = get_schema_view(
    openapi.Info(
        title="API Documentation",
        default_version='v1',
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

class SwaggerRenderer(SwaggerUIRenderer):
    template = 'swagger-ui.html'

class SwaggerUIView(SchemaView):
    renderer_classes = [SwaggerRenderer, SwaggerYAMLRenderer, SwaggerJSONRenderer, OpenAPIRenderer]
    @classmethod
    def without_ui(cls, cache_timeout=0, cache_kwargs=None):
        return cls.as_cached_view(cache_timeout, cache_kwargs, renderer_classes=cls.renderer_classes)
    
    @classmethod
    def with_ui(cls, cache_timeout=0, cache_kwargs=None):
        return cls.as_cached_view(cache_timeout, cache_kwargs, renderer_classes=cls.renderer_classes)
