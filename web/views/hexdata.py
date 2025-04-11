from rest_framework import views, status
from rest_framework.response import Response
import json
from web.models import GeographicArea, Station, Parameter, ParameterName
from web.utils.idw_interpolation import IDWInterpolator, generate_hexgrid, interpolate_hexgrid
from web.utils.logger import logger
from web.utils.response_utils import custom_response
from django.db.models import Max, F, Subquery, OuterRef
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..error_messages import VALIDATION_ERROR_MESSAGES, HEX_ERROR_MESSAGES

class HexagonDataAPIView(views.APIView):
    """API view to get interpolated data for hexagons"""
    
    @swagger_auto_schema(
        tags=['Interpolation Map'],
        operation_description="Get interpolated parameter data for hexagon grid",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parameter name slug (required)",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Interpolated parameter values for hexagons",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'hex_id': openapi.Schema(type=openapi.TYPE_STRING),
                                    'value': openapi.Schema(type=openapi.TYPE_NUMBER)
                                }
                            )
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: f"Bad Request: {VALIDATION_ERROR_MESSAGES['required']}",
            404: f"Not Found: {HEX_ERROR_MESSAGES['parameter_not_found']} or {HEX_ERROR_MESSAGES['no_station_data']}",
            500: f"Internal Server Error: {HEX_ERROR_MESSAGES['interpolation_error']}"
        }
    )
    def get(self, request, *args, **kwargs):
        # Get the parameter name from the request (now required)
        parameter_name_slug = request.query_params.get('parameter_name')
        
        # Check if parameter_name is provided
        if not parameter_name_slug:
            return custom_response(
                detail=VALIDATION_ERROR_MESSAGES['required'].format(field="Parameter name"),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        try:
            # Get the single geographic area
            area = GeographicArea.objects.first()
            
            if area:
                bounds = {
                    'north': area.north,
                    'south': area.south,
                    'east': area.east,
                    'west': area.west,
                }
                resolution = area.preferred_resolution
                
                # Check for custom polygon
                polygon_coords = None
                if area.coordinates:
                    try:
                        polygon_coords = json.loads(area.coordinates)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse coordinates: {e}")
                        return custom_response(
                            detail=HEX_ERROR_MESSAGES['parsing_failed'].format(error=str(e)),
                            status_code=status.HTTP_400_BAD_REQUEST,
                            success=False
                        )
            else:
                # If no area exists, return empty result
                return custom_response([])
        except Exception as e:
            logger.error(f"Error getting area: {e}")
            # If error with area, return empty result
            return custom_response([])
        
        try:
            # Get parameter name
            parameter_name = ParameterName.objects.filter(slug=parameter_name_slug).first()
            if not parameter_name:
                return custom_response(
                    detail=HEX_ERROR_MESSAGES['parameter_not_found'].format(parameter_name=parameter_name_slug),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Get latest parameters for each station of the specified name
            latest_params = Parameter.objects.filter(
                station=OuterRef('pk'),
                parameter_name=parameter_name
            ).order_by('-datetime').values('value')[:1]
            
            # Get stations with their latest parameter values
            stations = Station.objects.annotate(
                parameter_value=Subquery(latest_params)
            ).filter(parameter_value__isnull=False)
            
            if not stations:
                return custom_response(
                    detail=HEX_ERROR_MESSAGES['no_station_data'].format(parameter_name=parameter_name.name),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
                
            # Convert stations to dictionaries for the interpolator
            station_data = [
                {
                    'lat': station.lat,
                    'lng': station.lon,
                    'value': station.parameter_value  # Using the parameter value for interpolation
                }
                for station in stations
            ]
            
            # Create the interpolator with parameter name slug as the value field
            interpolator = IDWInterpolator(station_data, value_field='value')
            
            # Generate the hexgrid
            hexgrid = generate_hexgrid(bounds, resolution, polygon_coords=polygon_coords)
            
            # Interpolate values for each hexagon
            hex_data = interpolate_hexgrid(hexgrid, interpolator)
            
            # Convert to list format for response
            data_list = [
                {
                    'hex_id': hex_id,
                    **hex_values
                }
                for hex_id, hex_values in hex_data.items()
            ]
            
            # Return the data
            return custom_response(data_list)
            
        except Exception as e:
            logger.error(f"Error interpolating data: {e}")
            return custom_response(
                detail=HEX_ERROR_MESSAGES['interpolation_error'].format(error=str(e)),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            ) 