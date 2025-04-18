from django.contrib import admin
from django.db import models
from django.forms import widgets
from django.utils.safestring import mark_safe
from .models import Station, ParameterName, Parameter, GeographicArea
import os
from django.utils import timezone
from django.contrib.admin import SimpleListFilter

# Custom filters for day and month
class DayFilter(SimpleListFilter):
    title = 'Day'
    parameter_name = 'day'

    def lookups(self, request, model_admin):
        return [(str(i), str(i)) for i in range(1, 32)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(datetime__day=self.value())
        return queryset

class MonthFilter(SimpleListFilter):
    title = 'Month'
    parameter_name = 'month'

    def lookups(self, request, model_admin):
        months = [
            (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
            (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
            (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
        ]
        return [(str(k), v) for k, v in months]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(datetime__month=self.value())
        return queryset

# Register your models here.
admin.site.register(Station)
admin.site.register(ParameterName)

@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ('station', 'parameter_name', 'datetime', 'value')
    list_filter = ('station', 'parameter_name', 'datetime', DayFilter, MonthFilter)
    date_hierarchy = 'datetime'
    search_fields = ('station__name', 'station__number', 'parameter_name__name')

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

