from rest_framework import views, status
from rest_framework.response import Response
import json
from web.models import GeographicArea, Station, Parameter, ParameterType
from web.utils.idw_interpolation import IDWInterpolator, generate_hexgrid, interpolate_hexgrid
from web.utils.logger import logger
from web.utils.response_utils import custom_response
from django.db.models import Max, F, Subquery, OuterRef

class HexagonDataAPIView(views.APIView):
    """API view to get interpolated data for hexagons"""
    
    def get(self, request, *args, **kwargs):
        # Get the parameter type from the request or use default
        parameter_type_slug = request.query_params.get('parameter_type', 'aqi')
        
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
                        polygon_coords = None
            else:
                # Fall back to custom bounds from the request
                try:
                    bounds = {
                        'north': float(request.query_params.get('north', 90)),
                        'south': float(request.query_params.get('south', -90)),
                        'east': float(request.query_params.get('east', 180)),
                        'west': float(request.query_params.get('west', -180)),
                    }
                    resolution = int(request.query_params.get('resolution', 6))
                except (ValueError, TypeError) as e:
                    return custom_response(
                        detail=f"Invalid parameters: {str(e)}",
                        status_code=status.HTTP_400_BAD_REQUEST,
                        success=False
                    )
        except Exception as e:
            logger.error(f"Error getting area: {e}")
            # Fall back to custom bounds
            try:
                bounds = {
                    'north': float(request.query_params.get('north', 90)),
                    'south': float(request.query_params.get('south', -90)),
                    'east': float(request.query_params.get('east', 180)),
                    'west': float(request.query_params.get('west', -180)),
                }
                resolution = int(request.query_params.get('resolution', 6))
            except (ValueError, TypeError) as e:
                return custom_response(
                    detail=f"Invalid parameters: {str(e)}",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
        
        try:
            # Get parameter type
            parameter_type = ParameterType.objects.filter(slug=parameter_type_slug).first()
            if not parameter_type:
                return custom_response(
                    detail=f"Parameter type '{parameter_type_slug}' not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Get latest parameters for each station of the specified type
            latest_params = Parameter.objects.filter(
                station=OuterRef('pk'),
                parameter_type=parameter_type
            ).order_by('-datetime').values('value')[:1]
            
            # Get stations with their latest parameter values
            stations = Station.objects.annotate(
                parameter_value=Subquery(latest_params)
            ).filter(parameter_value__isnull=False)
            
            if not stations:
                return custom_response(
                    detail=f"No stations available with {parameter_type.name} data for interpolation",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
                
            # Convert stations to dictionaries for the interpolator
            station_data = [
                {
                    'lat': station.lat,
                    'lng': station.lon,
                    'aqi': station.parameter_value  # Using the parameter value for interpolation
                }
                for station in stations
            ]
            
            # Create the interpolator
            interpolator = IDWInterpolator(station_data)
            
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
                detail=f"Error interpolating data: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            ) 