from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import AUTH_ERROR_MESSAGES, PARAMETER_ERROR_MESSAGES
from ..models import Station, ParameterName, Parameter
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from django.db.models import Max
from django.conf import settings
from ..utils import weather_scraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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


class ParametersByStationView(APIView):
    """
    View for retrieving parameters by station number
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Stansiya raqami bo'yicha parametrlarni olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
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
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            '<param-slug>': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def get(self, request, station_number):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        parameters = Parameter.objects.filter(station=station)
        parameters_data = []
        
        for parameter in parameters:
            parameters_data.append({
                'id': parameter.id,
                'datetime': parameter.datetime,
                parameter.parameter_name.slug: parameter.value
            })
        
        return custom_response(
            data={
                'station': {
                    'number': station.number,
                    'name': station.name
                },
                'parameters': parameters_data
            },
            status_code=status.HTTP_200_OK
        )


class ParametersByNameAndStationView(APIView):
    """
    View for retrieving parameters by parameter name and station number
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Stansiya raqami va parametr nomi bo'yicha parametrlarni olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'parameter_name_slug',
                openapi.IN_PATH,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=True
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
                                'parameter_name_slug': openapi.Schema(type=openapi.TYPE_STRING),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'value': openapi.Schema(type=openapi.TYPE_NUMBER)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya yoki parametr nomi topilmadi",
        }
    )
    def get(self, request, station_number, parameter_name_slug):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        try:
            parameter_name = ParameterName.objects.get(slug=parameter_name_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        parameters = Parameter.objects.filter(station=station, parameter_name=parameter_name)
        parameters_data = []
        
        for parameter in parameters:
            parameters_data.append({
                'id': parameter.id,
                'datetime': parameter.datetime,
                'value': parameter.value
            })
        
        return custom_response(
            data={
                'station': {
                    'number': station.number,
                    'name': station.name
                },
                'parameter_name_slug': parameter_name.slug,
                'parameters': parameters_data
            },
            status_code=status.HTTP_200_OK
        )


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