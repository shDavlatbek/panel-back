from django.db import models
from django.utils import timezone
from django.utils.text import slugify
class Station(models.Model):
    number = models.CharField(max_length=250, unique=True)
    name = models.CharField(max_length=250)
    address = models.CharField(max_length=250)
    lon = models.FloatField()
    lat = models.FloatField()
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
