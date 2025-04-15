from rest_framework import views, status
from rest_framework.response import Response
import json
from web.models import GeographicArea, Station, Parameter, ParameterName
from web.utils.idw_interpolation import IDWInterpolator, generate_hexgrid, interpolate_hexgrid
from web.utils.logger import logger
from web.utils.response_utils import custom_response
from django.db.models import Max, F, Subquery, OuterRef, Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..error_messages import VALIDATION_ERROR_MESSAGES, HEX_ERROR_MESSAGES
from rest_framework.permissions import IsAuthenticated
from datetime import datetime, timedelta
from django.utils.dateparse import parse_datetime

class HexagonDataAPIView(views.APIView):
    """API view to get interpolated data for hexagons"""
    
    permission_classes = [IsAuthenticated]
    
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
            openapi.Parameter(
                'datetime',
                openapi.IN_QUERY,
                description="Datetime to use for parameters (UTC+5 format: YYYY-MM-DD HH:MM:SS). If not provided, latest values will be used.",
                type=openapi.TYPE_STRING,
                required=False
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
        
        # Get datetime parameter (optional)
        datetime_str = request.query_params.get('datetime')
        specific_datetime = None
        
        # Check if parameter_name is provided
        if not parameter_name_slug:
            return custom_response(
                detail=VALIDATION_ERROR_MESSAGES['required'].format(field="Parameter name"),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Parse datetime if provided
        if datetime_str:
            try:
                # Parse the datetime string
                specific_datetime = parse_datetime(datetime_str)
                if not specific_datetime:
                    return custom_response(
                        detail="Invalid datetime format. Use YYYY-MM-DD HH:MM:SS",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        success=False
                    )
                # Convert from UTC+5 to UTC for database query
                specific_datetime = specific_datetime - timedelta(hours=5)
                logger.info(f"Filtering for datetime: {specific_datetime}")
            except Exception as e:
                logger.error(f"Error parsing datetime: {e}")
                return custom_response(
                    detail=f"Error parsing datetime: {str(e)}",
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
            
            stations_with_values = []
            
            if specific_datetime:
                # For specific datetime, get all stations with that parameter at that time
                # Find the closest time for each station (within a window, e.g., ±1 hour)
                time_window = 1  # hour
                start_time = specific_datetime - timedelta(hours=time_window)
                end_time = specific_datetime + timedelta(hours=time_window)
                
                # Find parameters within the time window for each station
                station_params = {}
                
                # Get all parameters within the time window
                params = Parameter.objects.filter(
                    parameter_name=parameter_name,
                    datetime__gte=start_time,
                    datetime__lte=end_time
                ).select_related('station')
                
                # For each parameter, check if it's the closest to the target time for its station
                for param in params:
                    station_id = param.station.id
                    time_diff = abs((param.datetime - specific_datetime).total_seconds())
                    
                    if station_id not in station_params or time_diff < station_params[station_id]['time_diff']:
                        station_params[station_id] = {
                            'parameter': param,
                            'time_diff': time_diff
                        }
                
                # Convert to the format needed by the interpolator
                for station_id, data in station_params.items():
                    param = data['parameter']
                    stations_with_values.append({
                        'lat': param.station.lat,
                        'lng': param.station.lon,
                        'value': param.value,
                        'station_name': param.station.name,
                        'parameter_value': param.value,
                        'parameter_datetime': param.datetime + timedelta(hours=5)  # Convert back to UTC+5 for display
                    })
            else:
                # Get latest parameters for each station of the specified name
                latest_params = Parameter.objects.filter(
                    station=OuterRef('pk'),
                    parameter_name=parameter_name
                ).order_by('-datetime').values('value', 'datetime')[:1]
                
                # Get stations with their latest parameter values
                stations = Station.objects.annotate(
                    parameter_value=Subquery(latest_params.values('value')),
                    parameter_datetime=Subquery(latest_params.values('datetime'))
                ).filter(parameter_value__isnull=False)
                
                # Convert to the format needed by the interpolator
                for station in stations:
                    stations_with_values.append({
                        'lat': station.lat,
                        'lng': station.lon,
                        'value': station.parameter_value,
                        'station_name': station.name,
                        'parameter_value': station.parameter_value,
                        'parameter_datetime': station.parameter_datetime + timedelta(hours=5) if station.parameter_datetime else None
                    })
            
            if not stations_with_values:
                return custom_response(
                    detail=HEX_ERROR_MESSAGES['no_station_data'].format(parameter_name=parameter_name.name),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
                
            # Use the prepared station data for interpolation
            station_data = stations_with_values
            logger.info(f"Station data: {station_data}")
            
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
            
            # Return the data with metadata
            response_data = {
                'hexagons': data_list,
                'metadata': {
                    'parameter_name': parameter_name.name,
                    'parameter_slug': parameter_name.slug,
                    'datetime': datetime_str,
                    'stations_count': len(stations_with_values)
                }
            }
            
            return custom_response(response_data)
            
        except Exception as e:
            logger.error(f"Error interpolating data: {e}")
            return custom_response(
                detail=HEX_ERROR_MESSAGES['interpolation_error'].format(error=str(e)),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            ) 