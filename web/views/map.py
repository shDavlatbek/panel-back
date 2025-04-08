from django.shortcuts import render
from django.views.generic import TemplateView
from rest_framework.permissions import AllowAny

class MapView(TemplateView):
    """View to display the hexagonal grid interpolation map"""
    template_name = 'map.html'
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {}) 