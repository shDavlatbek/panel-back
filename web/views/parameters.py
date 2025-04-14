from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import AUTH_ERROR_MESSAGES
from ..models import Station, ParameterName, Parameter
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from django.db.models import Max, Avg
from ..utils import weather_scraper
from ..utils.logger import logger
from django.db.models import Q
from django.utils.dateparse import parse_datetime


class ParameterNameView(APIView):
    """
    View for retrieving all parameter names
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Barcha parametr nomlarini olish",
        responses={
            200: openapi.Response(
                description="Parametr nomlari ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'items': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'unit': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
        }
    )
    def get(self, request):
        parameter_names = ParameterName.objects.all()
        parameter_names_data = []
        
        for parameter_name in parameter_names:
            parameter_names_data.append({
                'slug': parameter_name.slug,
                'id': parameter_name.id,
                'name': parameter_name.name,
                'unit': parameter_name.unit
            })
        
        return custom_response(
            data={
                'items': parameter_names_data
            },
            status_code=status.HTTP_200_OK
        )


class ParametersView(APIView):
    """
    View for retrieving parameters for all stations
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Barcha stansiyalar parametrlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Boshlanish sanasi (UTC+5 vaqtida, 'YYYY-MM-DD HH:MM:SS' formatida)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Tugash sanasi (UTC+5 vaqtida, 'YYYY-MM-DD HH:MM:SS' formatida)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=False
            ),
            # openapi.Parameter(
            #     'include_empty',
            #     openapi.IN_QUERY,
            #     description="Bo'sh vaqt oraliqlarini ham qaytarish (true/false)",
            #     type=openapi.TYPE_BOOLEAN,
            #     default=False,
            #     required=False
            # ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Sahifa hajmi (pagination)",
                type=openapi.TYPE_INTEGER,
                default=100,
                required=False
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description="Sahifalashtirish uchun siljish (pagination)",
                type=openapi.TYPE_INTEGER,
                default=0,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Parametrlar ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'stations': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                ),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'station_number': openapi.Schema(type=openapi.TYPE_STRING),
                                            '<param-slug>': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                                        }
                                    )
                                ),
                                'pagination': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'offset': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'next': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                        'previous': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True)
                                    }
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
        }
    )
    def get(self, request):
        """
        Get parameters for all stations
        """
        return self._get_parameters(request, None)
        
    def _get_parameters(self, request, station_number=None):
        """
        Internal method to handle parameter retrieval
        """
        # Get query parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        param_name_slug = request.query_params.get('parameter_name')
        include_empty = request.query_params.get('include_empty', 'false').lower() == 'true'
        
        # Get pagination parameters
        try:
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))
        except ValueError:
            return custom_response(
                detail="limit va offset butun son bo'lishi kerak",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Validate required parameters
        if not start_date_str or not end_date_str:
            return custom_response(
                detail="start_date va end_date parametrlari talab qilinadi",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Handle timezone conversion (UTC+5 to UTC)
        start_date = parse_datetime(start_date_str)
        if not start_date:
            return custom_response(
                detail="start_date formati noto'g'ri. 'YYYY-MM-DD HH:MM:SS' formatida bo'lishi kerak",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        end_date = parse_datetime(end_date_str)
        if not end_date:
            return custom_response(
                detail="end_date formati noto'g'ri. 'YYYY-MM-DD HH:MM:SS' formatida bo'lishi kerak",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Convert from UTC+5 to UTC by subtracting 5 hours
        start_date = start_date - timedelta(hours=5)
        end_date = end_date - timedelta(hours=5)
            
        # Special case for 'avg' station
        if station_number == 'avg':
            return self._get_average_parameters(request, start_date, end_date, param_name_slug, include_empty, limit, offset)
        
        # Initialize filters
        filters = Q()
        
        # If station_number is provided, filter by station
        if station_number:
            try:
                station = Station.objects.get(number=station_number)
                filters &= Q(station=station)
            except Station.DoesNotExist:
                return custom_response(
                    detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
        
        # Add date filters
        filters &= Q(datetime__gte=start_date)
        filters &= Q(datetime__lte=end_date)
            
        # Add parameter name filter if provided
        parameter_names = []
        if param_name_slug:
            try:
                parameter_name = ParameterName.objects.get(slug=param_name_slug)
                filters &= Q(parameter_name=parameter_name)
                parameter_names = [parameter_name]
            except ParameterName.DoesNotExist:
                return custom_response(
                    detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
        else:
            # Get all parameter names if not specified
            parameter_names = ParameterName.objects.all()
        
        # Get filtered parameters
        parameters = Parameter.objects.filter(filters).select_related('station', 'parameter_name')
        
        # Get all stations data if station_number is not provided
        if station_number:
            stations_data = [{
                'number': station.number,
                'name': station.name
            }]
            stations = [station]
        else:
            # Get all unique stations from filtered parameters or all stations if no parameters
            station_ids = parameters.values_list('station_id', flat=True).distinct()
            stations = Station.objects.filter(id__in=station_ids) if station_ids.exists() else Station.objects.all()
            stations_data = [{
                'number': s.number,
                'name': s.name
            } for s in stations]
        
        # Generate a dictionary to hold data grouped by datetime
        parameters_by_datetime = {}
        
        # Generate all possible datetimes in the range
        current_dt = start_date
        while current_dt <= end_date:
            # Convert to UTC+5 for display
            local_dt = current_dt + timedelta(hours=5)
            
            # For each station and datetime, initialize an empty record
            if station_number:
                # Single station case
                parameters_by_datetime[local_dt.isoformat()] = {
                    'datetime': local_dt
                }
            else:
                # Multi-station case - we need a record for each station for each datetime
                for s in stations:
                    key = f"{local_dt.isoformat()}_{s.number}"
                    parameters_by_datetime[key] = {
                        'datetime': local_dt,
                        'station_number': s.number
                    }
            
            # Move to next hour
            current_dt = current_dt + timedelta(hours=1)
        
        # Now populate the actual parameter values
        for parameter in parameters:
            # Convert datetime from UTC to UTC+5 by adding 5 hours
            local_datetime = parameter.datetime + timedelta(hours=5)
            dt_key = local_datetime.isoformat()
            
            # For multi-station case, include station number in the key
            if not station_number:
                dt_key = f"{dt_key}_{parameter.station.number}"
            
            # Initialize the entry if it doesn't exist (should already exist from the loop above)
            if dt_key not in parameters_by_datetime:
                if station_number:
                    parameters_by_datetime[dt_key] = {
                        'datetime': local_datetime
                    }
                else:
                    parameters_by_datetime[dt_key] = {
                        'datetime': local_datetime,
                        'station_number': parameter.station.number
                    }
            
            # Add the parameter value, treating wind_direction = -1 as null
            if parameter.parameter_name.slug == 'wind_direction' and parameter.value == -1:
                parameters_by_datetime[dt_key][parameter.parameter_name.slug] = None
            else:
                parameters_by_datetime[dt_key][parameter.parameter_name.slug] = parameter.value
        
        # Convert dictionary to list and ensure all parameter names are included (null if missing)
        parameters_data = []
        param_slugs = [p.slug for p in parameter_names]
        
        for key, data in parameters_by_datetime.items():
            # Ensure all parameter names have a value (null if missing)
            for param_name in parameter_names:
                if param_name.slug not in data:
                    data[param_name.slug] = None
            
            # Check if all parameter values are null
            has_data = False
            for slug in param_slugs:
                if data.get(slug) is not None:
                    has_data = True
                    break
            
            # Add the entry if it has data or if include_empty is True
            if has_data or include_empty:
                parameters_data.append(data)
        
        # Sort by datetime and station_number (if applicable)
        parameters_data.sort(key=lambda x: (x['datetime'], x.get('station_number', '')))
        
        # Calculate total count before pagination
        total_count = len(parameters_data)
        
        # Apply pagination
        paginated_data = parameters_data[offset:offset + limit] if parameters_data else []
        
        # Calculate next and previous page offsets
        next_offset = offset + limit if offset + limit < total_count else None
        previous_offset = offset - limit if offset > 0 else None
        
        # Return response with stations data and parameters
        result_data = {
            'items': paginated_data,
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'next': next_offset,
            'previous': previous_offset
            
        }
        
        if station_number:
            result_data['station'] = stations_data[0]
        else:
            result_data['stations'] = stations_data
        
        return custom_response(
            data=result_data,
            status_code=status.HTTP_200_OK
        )
    
    def _get_average_parameters(self, request, start_date, end_date, param_name_slug, include_empty=False, limit=100, offset=0):
        """
        Calculate average values for all stations or specific parameter
        between start_date and end_date.
        """
        filters = Q()
        
        # Add date filters
        filters &= Q(datetime__gte=start_date)
        filters &= Q(datetime__lte=end_date)
            
        # Filter by parameter name if provided
        if param_name_slug:
            try:
                parameter_name = ParameterName.objects.get(slug=param_name_slug)
                filters &= Q(parameter_name=parameter_name)
                parameter_names = [parameter_name]
            except ParameterName.DoesNotExist:
                return custom_response(
                    detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
        else:
            # Get all parameter names if not specified
            parameter_names = ParameterName.objects.all()
        
        # Generate a dictionary to hold data grouped by datetime
        parameters_by_datetime = {}
        
        # Generate all possible hours in the range
        current_dt = start_date
        while current_dt <= end_date:
            # Convert to UTC+5 for display
            local_dt = current_dt + timedelta(hours=5)
            
            # Initialize an empty record for this datetime
            parameters_by_datetime[local_dt.isoformat()] = {
                'datetime': local_dt
            }
            
            # Move to next hour
            current_dt = current_dt + timedelta(hours=1)
        
        # Calculate averages for each parameter name and each hour
        for param_name in parameter_names:
            param_filters = filters & Q(parameter_name=param_name)
            
            # Group by hour and calculate average
            current_dt = start_date
            while current_dt <= end_date:
                hour_filters = param_filters & Q(datetime__gte=current_dt) & Q(datetime__lt=current_dt + timedelta(hours=1))
                avg_value = Parameter.objects.filter(hour_filters).aggregate(avg_value=Avg('value'))['avg_value']
                
                # Convert datetime from UTC to UTC+5 by adding 5 hours
                local_dt = current_dt + timedelta(hours=5)
                dt_key = local_dt.isoformat()
                
                # Add the parameter value if there is data, otherwise keep as null
                if avg_value is not None:
                    # Special handling for wind_direction: if avg_value is -1, set to null
                    if param_name.slug == 'wind_direction' and avg_value == -1:
                        parameters_by_datetime[dt_key][param_name.slug] = None
                    else:
                        parameters_by_datetime[dt_key][param_name.slug] = round(avg_value, 2)
                else:
                    parameters_by_datetime[dt_key][param_name.slug] = None
                
                # Move to next hour
                current_dt = current_dt + timedelta(hours=1)
        
        # Convert dictionary to list, filtering out entries without data if requested
        parameters_data = []
        param_slugs = [p.slug for p in parameter_names]
        
        for key, data in parameters_by_datetime.items():
            # Check if all parameter values are null
            has_data = False
            for slug in param_slugs:
                if data.get(slug) is not None:
                    has_data = True
                    break
            
            # Add the entry if it has data or if include_empty is True
            if has_data or include_empty:
                parameters_data.append(data)
        
        # Sort by datetime
        parameters_data.sort(key=lambda x: x['datetime'])
        
        # Calculate total count before pagination
        total_count = len(parameters_data)
        
        # Apply pagination
        paginated_data = parameters_data[offset:offset + limit] if parameters_data else []
        
        # Calculate next and previous page offsets
        next_offset = offset + limit if offset + limit < total_count else None
        previous_offset = offset - limit if offset > 0 else None
        
        return custom_response(
            data={
                'station': {
                    'number': 'avg',
                    'name': 'Average of all stations'
                },
                'items': paginated_data,
                'count': total_count,
                'limit': limit,
                'offset': offset,
                'next': next_offset,
                'previous': previous_offset
            },
            status_code=status.HTTP_200_OK
        )



class StationParametersView(APIView):
    """
    View for retrieving parameters for a specific station
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Ma'lum stansiya parametrlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami (avg - barcha stansiyalar o'rtachasi uchun)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Boshlanish sanasi (UTC+5 vaqtida, 'YYYY-MM-DD HH:MM:SS' formatida)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Tugash sanasi (UTC+5 vaqtida, 'YYYY-MM-DD HH:MM:SS' formatida)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=False
            ),
            # openapi.Parameter(
            #     'include_empty',
            #     openapi.IN_QUERY,
            #     description="Bo'sh vaqt oraliqlarini ham qaytarish (true/false)",
            #     type=openapi.TYPE_BOOLEAN,
            #     default=False,
            #     required=False
            # ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="Sahifa hajmi (pagination)",
                type=openapi.TYPE_INTEGER,
                default=100,
                required=False
            ),
            openapi.Parameter(
                'offset',
                openapi.IN_QUERY,
                description="Sahifalashtirish uchun siljish (pagination)",
                type=openapi.TYPE_INTEGER,
                default=0,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Parametrlar ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            '<param-slug>': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                                        }
                                    )
                                ),
                                'pagination': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'limit': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'offset': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'next': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                        'previous': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True)
                                    }
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def get(self, request, station_number):
        """
        Get parameters for a specific station
        """
        params_view = ParametersView()
        return params_view._get_parameters(request, station_number)


class ParameterScrapeView(APIView):
    """
    View for scraping parameters from weather website
    """
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['post']  # Explicitly allow only POST method
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Parametrlarni veb-saytdan olish va ma'lumotlar bazasiga saqlash",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=None,
            properties={
                'station_numbers': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                    default=[38264, 38141, 38023, 38149, 38146, 38265, 38263, 38262],
                    description="Stansiya raqamlari ro'yxati (ixtiyoriy, ko'rsatilmasa barcha stansiyalar uchun)"
                ),
                'max_concurrent': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Maksimal parallellik soni",
                    default=10000,
                    nullable=True
                )
            }
        ),
        responses={
            200: openapi.Response(
                description="Parametrlar muvaffaqiyatli olindi va saqlandi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'items': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'station_number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'station_name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'parameters_added': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'start_date': openapi.Schema(type=openapi.TYPE_STRING),
                                            'end_date': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov formati noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def post(self, request):
        """
        POST endpoint to fetch and store weather parameters from external source.
        
        This method:
        1. Gets station numbers from the request (or uses defaults)
        2. Fetches the latest data for each station
        3. Processes and stores the data as Parameter objects
        4. Returns a summary of what was processed
        """
        # Get parameters from request
        station_numbers = request.data.get('station_numbers', [38264, 38141, 38023, 38149, 38146, 38265, 38263, 38262])
        max_concurrent = request.data.get('max_concurrent', 10000)
        
        # If station_numbers is empty, get all stations
        if not station_numbers:
            stations = Station.objects.all()
        else:
            stations = Station.objects.filter(number__in=station_numbers)
        
        if not stations.exists():
            return custom_response(
                detail="Belgilangan stansiyalar topilmadi",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process each station
        stations_processed = []
        
        try:
            # Process each station one by one
            for station in stations:
                logger.info(f"Processing station {station.number} ({station.name})")
                
                # Find the last parameter datetime for this station (if any)
                last_parameter = Parameter.objects.filter(station=station).aggregate(Max('datetime'))
                start_date = last_parameter['datetime__max'] + timedelta(hours=1) if last_parameter['datetime__max'] else None
                
                if not start_date:
                    # If no parameters exist, start from default date or station's data_from field
                    if hasattr(station, 'data_from') and station.data_from:
                        start_date = station.data_from
                    else:
                        start_date = datetime(2011, 1, 1)
                
                # Format date for the scraper
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = datetime.now().strftime('%Y-%m-%d')
                
                logger.info(f"Fetching data for station {station.number} from {start_date_str} to {end_date_str}")
                
                # Fetch weather data using the scraper utility
                weather_data = loop.run_until_complete(
                    weather_scraper.get_weather_data_async(
                        station_id=station.number,
                        start_date_str=start_date_str,
                        end_date_str=end_date_str,
                        max_concurrent=max_concurrent
                    )
                )
                
                # Process and save the scraped data
                parameters_added = self._process_weather_data(station, weather_data)
                
                # Add to processed stations list
                stations_processed.append({
                    'station_number': station.number,
                    'station_name': station.name,
                    'parameters_added': parameters_added,
                    'start_date': start_date_str,
                    'end_date': end_date_str
                })
                
                logger.info(f"Added {parameters_added} parameters for station {station.number}")
                
        finally:
            # Close the event loop
            loop.close()
        
        return custom_response(
            data={
                'items': stations_processed
            },
            status_code=status.HTTP_200_OK
        )
    
    def _process_weather_data(self, station, weather_data):
        """
        Process and save weather data to the database.
        
        Args:
            station (Station): The station model object
            weather_data (DataFrame): Pandas DataFrame with weather data
            
        Returns:
            int: Number of parameters added
        """
        parameters_added = 0
        
        if weather_data.empty:
            logger.warning(f"No weather data for station {station.number}")
            return parameters_added
        
        # Define parameter name mappings - each will become a Parameter record
        parameter_mappings = {
            # Format: "dataframe_column": (parameter_slug, custom_processing_function)
            "temp": ("temp", self._convert_to_float),
            "wind_speed": ("wind_speed", self._process_wind_speed),
            "wind_direction": ("wind_direction", self._process_wind_direction),
            "pressure": ("pressure", self._convert_to_float),
            "f": ("humidity", self._convert_to_float),  # f column is humidity percentage
            "R": ("rainfall", self._process_rainfall),  # R column is rainfall in mm
            "Te": ("ef_temp", self._convert_to_float),  # Te is effective temperature
            "phenomena": ("dust_storm", self._process_dust_storm)  # Process phenomena for dust storms
        }
        
        # Get parameter name objects ahead of time
        parameter_name_objects = {}
        for _, (slug, _) in parameter_mappings.items():
            try:
                parameter_name_objects[slug] = ParameterName.objects.get(slug=slug)
            except ParameterName.DoesNotExist:
                logger.error(f"Parameter name does not exist: {slug}")
        
        # Track overall progress for large datasets
        total_rows = len(weather_data)
        logger.info(f"Processing {total_rows} records for station {station.number}")
        
        # Collect parameters to create or update
        parameters_to_create = []
        
        # Extract all datetimes for lookup
        all_datetimes = weather_data['datetime'].dropna().unique().tolist()
        
        # Build an efficient lookup for existing parameters - query once instead of for each parameter
        existing_parameters = {}
        
        # Query existing parameters for this station and the given dates (one query per parameter type)
        for slug, param_name_obj in parameter_name_objects.items():
            # Get all existing parameters for this station, parameter type, and date range
            params = Parameter.objects.filter(
                station=station, 
                parameter_name=param_name_obj,
                datetime__in=all_datetimes
            ).values('id', 'datetime', 'value')
            
            # Build lookup dictionary by datetime
            for param in params:
                key = (slug, param['datetime'].isoformat())
                existing_parameters[key] = param
        
        # Process each row of weather data
        for index, row in weather_data.iterrows():
            # Skip invalid rows
            if row['datetime'] is None:
                continue
            
            # Process each parameter type
            for column, (slug, processor) in parameter_mappings.items():
                # Skip if the parameter name doesn't exist
                if slug not in parameter_name_objects:
                    continue
                
                try:
                    # Get the parameter name object
                    parameter_name = parameter_name_objects[slug]
                    
                    # For most parameters, skip empty values
                    # For rainfall and dust_storm, we'll process even if empty
                    if column not in row or pd.isna(row[column]):
                        if slug == "rainfall" or slug == "dust_storm":
                            # For rainfall and dust_storm, we'll still process
                            value = processor(None)
                        else:
                            # For other parameters, skip if empty
                            continue
                    else:
                        # Process the value using the specified processor function
                        value = processor(row[column])
                    
                    # Skip if value processing returned None
                    if value is None:
                        continue
                    
                    # Check if parameter already exists
                    key = (slug, row['datetime'].isoformat())
                    if key in existing_parameters:
                        # Parameter exists, update if needed (will be handled separately)
                        continue
                    else:
                        # Parameter doesn't exist, add to bulk create list
                        parameters_to_create.append(
                            Parameter(
                                station=station,
                                parameter_name=parameter_name,
                                datetime=row['datetime'],
                                value=value
                            )
                        )
                        parameters_added += 1
                        
                except Exception as e:
                    logger.warning(f"Error processing {column} value: {row[column]} - {e}")
            
            # Log progress for large datasets
            if index > 0 and index % 1000 == 0:
                # Every 1000 rows, do a bulk create to avoid memory issues
                if parameters_to_create:
                    Parameter.objects.bulk_create(parameters_to_create, batch_size=1000, ignore_conflicts=True)
                    logger.info(f"Created {len(parameters_to_create)} parameters in bulk")
                    parameters_to_create = []
                
                logger.info(f"Processed {index}/{total_rows} records for station {station.number}")
        
        # Final bulk create for remaining parameters
        if parameters_to_create:
            # Use batch_size for large number of objects (SQLite has limit around 999)
            Parameter.objects.bulk_create(parameters_to_create, batch_size=1000, ignore_conflicts=True)
            logger.info(f"Created {len(parameters_to_create)} parameters in final bulk create")
        
        return parameters_added
    
    def _convert_to_float(self, value):
        """Convert a value to float, handling string formatting."""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Remove any non-numeric characters (except decimal point and minus)
            clean_value = ''.join(c for c in value if c.isdigit() or c in ['.', '-'])
            return float(clean_value) if clean_value else None
        return None
    
    def _process_wind_direction(self, value):
        """
        Convert wind direction from Cyrillic text to numerical degrees.
        
        Args:
            value: The wind direction value (e.g., 'С', 'СВ', etc.)
            
        Returns:
            float: Direction in degrees (0-359) or -1 for calm/no wind
        """
        # Wind direction mapping: Cyrillic text to degrees
        wind_direction_mapping = {
            'С': 0,     # North
            'СВ': 45,   # Northeast
            'В': 90,    # East
            'ЮВ': 135,  # Southeast
            'Ю': 180,   # South
            'ЮЗ': 225,  # Southwest
            'З': 270,   # West
            'СЗ': 315,  # Northwest
            'штиль': -1 # Calm
        }
        
        if isinstance(value, str):
            value = value.strip()
            # Convert wind direction from text to degrees
            if value in wind_direction_mapping:
                return wind_direction_mapping[value]
        
        # Handle empty or unknown values
        return -1
        
    def _process_wind_speed(self, value):
        """
        Process wind speed values, handling special formatting like "10 {20}".
        
        Args:
            value: The wind speed value
            
        Returns:
            float: Wind speed as a float, or None if invalid
        """
        if value is None or value == '':
            return None
            
        if isinstance(value, (int, float)):
            return float(value)
            
        if isinstance(value, str):
            # Extract the first number if format is like "10 {20}"
            if '{' in value:
                # Get everything before the first '{'
                value = value.split('{')[0].strip()
            
            # Try to convert to float
            try:
                return float(value)
            except ValueError:
                # If it still has non-numeric characters, use the general cleaner
                clean_value = ''.join(c for c in value if c.isdigit() or c in ['.', '-'])
                return float(clean_value) if clean_value else None
        
        return None
        
    def _process_rainfall(self, value):
        """
        Process rainfall values, handling empty values.
        
        Args:
            value: The rainfall value
            
        Returns:
            float: Rainfall as a float, or -1 if empty
        """
        if value is None or value == '':
            return -1.0  # Return -1 for empty rainfall values
            
        if isinstance(value, (int, float)):
            return float(value)
            
        if isinstance(value, str):
            if value.strip() == '':
                return -1.0
                
            # Try to convert to float
            try:
                return float(value)
            except ValueError:
                # If it has non-numeric characters, use the general cleaner
                clean_value = ''.join(c for c in value if c.isdigit() or c in ['.', '-'])
                return float(clean_value) if clean_value else -1.0
        
        return -1.0
        
    def _process_dust_storm(self, value):
        """
        Process phenomena field to detect dust storms.
        
        Args:
            value: The phenomena value
            
        Returns:
            int: 1 if dust storm detected, 0 otherwise
        """
        if value is None:
            return 0
            
        if isinstance(value, str) and "пыльная буря" in value.lower():
            return 1
            
        return 0
    
    def _get_default_unit_for_parameter(self, slug):
        """Get default unit for parameter based on slug"""
        units = {
            'temp': '°C',
            'wind_speed': 'm/s',
            'wind_direction': '°',
            'pressure': 'mm Hg',
            'humidity': '%',
            'rainfall': 'mm',
            'ef_temp': '°C',
            'dust_storm': 'n'
        }
        return units.get(slug, '') 