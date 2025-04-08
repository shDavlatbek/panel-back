from django.http import JsonResponse
from rest_framework import views, status
from rest_framework.response import Response
import json
from web.models import GeographicArea
from web.utils.idw_interpolation import generate_hexgrid
from web.utils.logger import logger
from web.utils.response_utils import custom_response

class HexGridAPIView(views.APIView):
    """API view to generate hexagonal grid as GeoJSON"""
    
    def get(self, request, *args, **kwargs):
        try:
            # Get the single geographic area (assumes only one exists)
            area = GeographicArea.objects.first()
            
            if area:
                bounds = {
                    'north': area.north,
                    'south': area.south,
                    'east': area.east,
                    'west': area.west,
                }
                resolution = area.preferred_resolution
                
                # Check if the area has custom polygon coordinates
                polygon_coords = None
                if area.coordinates:
                    try:
                        # Parse the polygon coordinates from the area
                        polygon_coords = json.loads(area.coordinates)
                        
                        # Generate the hexagonal grid using the polygon coordinates
                        hexgrid = generate_hexgrid(bounds, resolution, polygon_coords=polygon_coords)
                        return custom_response(hexgrid['geojson'])
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse coordinates JSON: {e}")
                
                # If no polygon or parsing failed, fall back to bounding box
                hexgrid = generate_hexgrid(bounds, resolution)
                return custom_response(hexgrid['geojson'])
            else:
                # If no area exists, validate the custom bounds from the request
                try:
                    bounds = {
                        'north': float(request.query_params.get('north', 90)),
                        'south': float(request.query_params.get('south', -90)),
                        'east': float(request.query_params.get('east', 180)),
                        'west': float(request.query_params.get('west', -180)),
                    }
                    resolution = int(request.query_params.get('resolution', 6))
                    
                    # Generate the hexgrid with custom bounds
                    hexgrid = generate_hexgrid(bounds, resolution)
                    
                    # Return the GeoJSON feature collection
                    return custom_response(hexgrid['geojson'])
                except (ValueError, TypeError) as e:
                    return custom_response(
                        detail=f"Invalid parameters: {str(e)}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        success=False
                    )
                
        except Exception as e:
            logger.error(f"Error generating hexgrid: {e}")
            return custom_response(
                detail=f"Failed to generate hexgrid: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            ) 