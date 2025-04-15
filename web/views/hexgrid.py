from django.http import JsonResponse
from rest_framework import views, status
from rest_framework.response import Response
import json
import geojson
from web.models import GeographicArea, ParameterName
from web.utils.idw_interpolation import generate_hexgrid
from web.utils.logger import logger
from web.utils.response_utils import custom_response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..error_messages import VALIDATION_ERROR_MESSAGES, HEX_ERROR_MESSAGES
from rest_framework.permissions import IsAuthenticated
class HexGridAPIView(views.APIView):
    """API view to generate hexagonal grid as GeoJSON"""
    
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Interpolation Map'],
        operation_description="Generate hexagonal grid as GeoJSON",
        responses={
            200: openapi.Response(
                description="Hexagonal grid as GeoJSON",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: f"Bad Request: {HEX_ERROR_MESSAGES['invalid_bounds']}",
            500: f"Internal Server Error: {HEX_ERROR_MESSAGES['grid_generation_error']}"
        }
    )
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
                        return custom_response(
                            detail=HEX_ERROR_MESSAGES['parsing_failed'].format(error=str(e)),
                            status_code=status.HTTP_400_BAD_REQUEST,
                            success=False
                        )
                
                # If no polygon or parsing failed, fall back to bounding box
                hexgrid = generate_hexgrid(bounds, resolution)
                return custom_response(hexgrid['geojson'])
            else:
                # If no area exists, return empty result
                return custom_response(
                    geojson.FeatureCollection([])
                )
                
        except Exception as e:
            logger.error(f"Error generating hexgrid: {e}")
            return custom_response(
                detail=HEX_ERROR_MESSAGES['grid_generation_error'].format(error=str(e)),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            ) 