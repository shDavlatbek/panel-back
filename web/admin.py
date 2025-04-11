from django.contrib import admin
from django.db import models
from django.forms import widgets
from django.utils.safestring import mark_safe
from .models import Station, ParameterName, Parameter, GeographicArea
import os

# Register your models here.
admin.site.register(Station)
admin.site.register(ParameterName)
admin.site.register(Parameter)

class MapPolygonWidget(widgets.Textarea):
    """
    Custom widget that displays a Leaflet map for drawing polygons.
    """
    template_name = os.path.join('admin', 'map_polygon_widget.html')
    
    class Media:
        css = {
            'all': (
                'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
                'https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.css',
            )
        }
        js = (
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js',
        )
    
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context['widget']['type'] = 'hidden'  # Hide the original textarea
        context['map_id'] = f'map_{name}'
        context['display_id'] = f'display_{name}'
        return context

@admin.register(GeographicArea)
class GeographicAreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'north', 'south', 'east', 'west', 'preferred_resolution',)
    list_editable = ('preferred_resolution',)
    formfield_overrides = {
        models.TextField: {'widget': MapPolygonWidget},
    }
    fieldsets = (
        (None, {
            'fields': ('name', 'preferred_resolution',)
        }),
        ('Boundary', {
            'fields': ('coordinates', 'north', 'south', 'east', 'west'),
        }),
    )
    readonly_fields = ('north', 'south', 'east', 'west')
    # def has_add_permission(self, request):
    #     return False
    # def has_delete_permission(self, request, obj=None):
    #     return False
    
    class Media:
        css = {
            'all': ('css/admin_map.css',)
        }
        js = ('js/admin_map.js',)

