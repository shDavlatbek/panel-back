import json
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

class Station(models.Model):
    number = models.IntegerField(unique=True)
    name = models.CharField(max_length=250)
    height = models.FloatField()
    lat = models.FloatField()
    lon = models.FloatField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.number})"
    
    @property
    def parameter_types(self):
        return ParameterType.objects.filter(parameters__station=self).distinct()

class ParameterType(models.Model):
    name = models.CharField(max_length=250)
    slug = models.SlugField(max_length=250, unique=True)
    unit = models.CharField(max_length=250)

    def __str__(self):
        return f"{self.name} ({self.unit})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Parameter(models.Model):
    station = models.ForeignKey('Station', on_delete=models.CASCADE, related_name='parameters')
    parameter_type = models.ForeignKey('ParameterType', on_delete=models.CASCADE, related_name='parameters')
    datetime = models.DateTimeField()
    value = models.FloatField()

    def __str__(self):
        return f"{self.station.number} - {self.datetime}"

    class Meta:
        ordering = ['-datetime']

class GeographicArea(models.Model):
    """
    Geographic area model for defining bounds and polygon areas for hexagonal grid generation.
    """
    name = models.CharField(max_length=100)
    
    # Bounding box coordinates
    north = models.FloatField(help_text="North latitude bound")
    south = models.FloatField(help_text="South latitude bound")
    east = models.FloatField(help_text="East longitude bound")
    west = models.FloatField(help_text="West longitude bound")
    
    # Optional polygon coordinates stored as GeoJSON-compatible string
    coordinates = models.TextField(blank=True, null=True, 
                                help_text="GeoJSON-compatible polygon coordinates array")
    
    # H3 resolution for hexagon generation (0-15, lower means larger hexagons)
    preferred_resolution = models.PositiveSmallIntegerField(default=6, 
                                                         help_text="H3 resolution (0-15)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Calculate bounding box from coordinates if available
        if self.coordinates:
            try:
                coords = json.loads(self.coordinates)
                if coords and len(coords) > 0:
                    # No coordinate swapping - assume coordinates are always stored in [lng, lat] format
                    # as correctly provided by the admin widget
                    
                    # Extract lng/lat for bounding box (maintaining the format [lng, lat])
                    lngs = [p[0] for p in coords]
                    lats = [p[1] for p in coords]
                    
                    self.west = min(lngs)
                    self.east = max(lngs)
                    self.south = min(lats)
                    self.north = max(lats)
            except (json.JSONDecodeError, IndexError):
                pass
                
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Geographic Area"
        verbose_name_plural = "Geographic Areas"
