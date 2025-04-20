from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Avg, Min, Max, StdDev, Count, Q
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats
from itertools import combinations

from ..utils import custom_response
from ..error_messages import AUTH_ERROR_MESSAGES
from ..models import Station, ParameterName, Parameter


class StatisticsView(APIView):
    """
    View for retrieving statistics for parameters
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Statistics'],
        operation_description="Ma'lum parametr uchun statistika ma'lumotlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi (temp, humidity, pressure, rainfall, wind_speed, ef_temp, dust_storm)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Statistika hisoblanadigan yil (start_date va end_date o'rniga ishlatiladi)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'start_date',
                openapi.IN_QUERY,
                description="Boshlang'ich sana (UTC+5 vaqti, 'YYYY-MM-DD HH:MM:SS' formatida, year ko'rsatilmasa talab qilinadi)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'end_date',
                openapi.IN_QUERY,
                description="Tugash sanasi (UTC+5 vaqti, 'YYYY-MM-DD HH:MM:SS' formatida, year ko'rsatilmasa talab qilinadi)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'station_number',
                openapi.IN_QUERY,
                description="Stansiya raqami (ixtiyoriy, ko'rsatilmasa barcha stansiyalar uchun hisoblash amalga oshiriladi)",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Statistika muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'parameter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                        'unit': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING, nullable=True)
                                    },
                                    nullable=True
                                ),
                                'period': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'year': openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
                                        'start_date': openapi.Schema(type=openapi.TYPE_STRING),
                                        'end_date': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'statistics': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'mean': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'median': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'mode': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER)),
                                        'min': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'max': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'std_dev': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'variance': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'coefficient_of_variation': openapi.Schema(type=openapi.TYPE_NUMBER)
                                    }
                                ),
                                'monthly_mode': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'month': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'month_name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'mode': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER)),
                                            'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: f"Ruxsat mavjud emas: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: "Parametr nomi yoki stansiya topilmadi",
        }
    )
    def get(self, request):
        # Get query parameters
        param_name_slug = request.query_params.get('parameter_name')
        year_str = request.query_params.get('year')
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        station_number = request.query_params.get('station_number')
        
        # Validate parameter_name
        if not param_name_slug:
            return custom_response(
                detail="parameter_name parametri talab qilinadi",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
            
        # Process the date range based on parameters
        # If year is provided, use it; otherwise, use start_date and end_date
        selected_year = None
        if year_str:
            try:
                selected_year = int(year_str)
                start_date = datetime(selected_year, 1, 1) - timedelta(hours=5)  # UTC+5 to UTC
                end_date = datetime(selected_year + 1, 1, 1) - timedelta(seconds=1) - timedelta(hours=5)  # UTC+5 to UTC
            except ValueError:
                return custom_response(
                    detail="year butun son bo'lishi kerak",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
        else:
            # When year is not provided, start_date and end_date are required
            if not start_date_str or not end_date_str:
                return custom_response(
                    detail="year ko'rsatilmaganda start_date va end_date parametrlari talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Parse dates
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
        
        # Check if parameter name exists
        try:
            param_name = ParameterName.objects.get(slug=param_name_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=f"'{param_name_slug}' parametri topilmadi",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Initialize filters
        filters = Q(parameter_name=param_name, datetime__gte=start_date, datetime__lte=end_date)
        
        # If station_number is provided, filter by station
        station = None
        if station_number:
            try:
                station = Station.objects.get(number=station_number)
                filters &= Q(station=station)
            except Station.DoesNotExist:
                return custom_response(
                    detail=f"'{station_number}' stansiyasi topilmadi",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
        
        # Get parameters
        parameters = Parameter.objects.filter(filters).order_by('datetime')
        
        # Check if parameters exist
        if not parameters.exists():
            return custom_response(
                detail="Berilgan parametrlar va vaqt davri uchun ma'lumotlar topilmadi",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Calculate basic statistics
        values = list(parameters.values_list('value', flat=True))
        values_df = pd.DataFrame({
            'value': values,
            'datetime': list(parameters.values_list('datetime', flat=True))
        })
        
        # Calculate mode
        mode_result = stats.mode(values)
        mode_values = [float(mode_result.mode[0])]
        
        # Convert data for statistics
        stats_data = {
            'mean': float(parameters.aggregate(Avg('value'))['value__avg']),
            'min': float(parameters.aggregate(Min('value'))['value__min']),
            'max': float(parameters.aggregate(Max('value'))['value__max']),
            'std_dev': float(parameters.aggregate(StdDev('value'))['value__stddev'] or 0),
            'count': parameters.count(),
            'median': float(np.median(values)),
            'mode': mode_values,
            'variance': float(np.var(values)),
            'coefficient_of_variation': float(np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0,
        }
        
        # Calculate monthly mode
        # Add UTC+5 time
        values_df['datetime_utc5'] = values_df['datetime'] + pd.Timedelta(hours=5)
        
        # Extract month from datetime
        values_df['month'] = values_df['datetime_utc5'].dt.month
        values_df['year'] = values_df['datetime_utc5'].dt.year
        
        # Initialize monthly mode data
        monthly_mode = []
        month_names = [
            'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
            'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'
        ]
        
        # Use the selected year or the most recent year in the data
        target_year = selected_year
        if not target_year:
            years = sorted(values_df['year'].unique())
            if years:
                target_year = years[-1]
        
        if target_year:
            year_data = values_df[values_df['year'] == target_year]
            
            for month in range(1, 13):
                month_data = year_data[year_data['month'] == month]
                
                if len(month_data) > 0:
                    month_values = month_data['value'].tolist()
                    month_mode = stats.mode(month_values)
                    month_mode_values = [float(val) for val in month_mode.mode]
                    
                    monthly_mode.append({
                        'month': month,
                        'month_name': month_names[month - 1],
                        'mode': month_mode_values,
                        'count': len(month_data)
                    })
                else:
                    monthly_mode.append({
                        'month': month,
                        'month_name': month_names[month - 1],
                        'mode': [],
                        'count': 0
                    })
        
        # Prepare period information
        period = {
            'start_date': (start_date + timedelta(hours=5)).isoformat(),
            'end_date': (end_date + timedelta(hours=5)).isoformat()
        }
        
        # Add year to period info if selected
        if selected_year:
            period['year'] = selected_year
        
        # Prepare response
        result = {
            'parameter': {
                'name': param_name.name,
                'slug': param_name.slug,
                'unit': param_name.unit
            },
            'period': period,
            'statistics': stats_data,
            'monthly_mode': monthly_mode
        }
        
        # Add station information if provided
        if station:
            result['station'] = {
                'number': str(station.number),
                'name': station.name
            }
        else:
            result['station'] = None
        
        return custom_response(
            data=result,
            status_code=status.HTTP_200_OK
        )


class MonthlyStatsView(APIView):
    """
    View for retrieving monthly statistics for parameters
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Statistics'],
        operation_description="Ma'lum parametr uchun oylik statistikani olish",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi (temp, humidity, pressure, rainfall, wind_speed, ef_temp, dust_storm)",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Oylik statistika olinadigan yil",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'station_number',
                openapi.IN_QUERY,
                description="Stansiya raqami (ixtiyoriy, ko'rsatilmasa barcha stansiyalar uchun hisoblash amalga oshiriladi)",
                type=openapi.TYPE_STRING,
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Oylik statistika muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'parameter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                        'unit': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING, nullable=True)
                                    },
                                    nullable=True
                                ),
                                'year': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'monthly_data': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'month': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'month_name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'mean': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'median': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'mode': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER)),
                                            'min': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'max': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'std_dev': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'count': openapi.Schema(type=openapi.TYPE_INTEGER)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: f"Ruxsat mavjud emas: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: "Parametr nomi yoki stansiya topilmadi",
        }
    )
    def get(self, request):
        # Get query parameters
        param_name_slug = request.query_params.get('parameter_name')
        year_str = request.query_params.get('year')
        station_number = request.query_params.get('station_number')
        
        # Validate required parameters
        if not param_name_slug or not year_str:
            return custom_response(
                detail="parameter_name va year parametrlari talab qilinadi",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Parse year
        try:
            year = int(year_str)
        except ValueError:
            return custom_response(
                detail="year butun son bo'lishi kerak",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Check if parameter name exists
        try:
            param_name = ParameterName.objects.get(slug=param_name_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=f"'{param_name_slug}' parametri topilmadi",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Define start and end dates for the year
        start_date = datetime(year, 1, 1) - timedelta(hours=5)  # UTC+5 to UTC
        end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1) - timedelta(hours=5)  # UTC+5 to UTC
        
        # Initialize filters
        filters = Q(parameter_name=param_name, datetime__gte=start_date, datetime__lte=end_date)
        
        # If station_number is provided, filter by station
        station = None
        if station_number:
            try:
                station = Station.objects.get(number=station_number)
                filters &= Q(station=station)
            except Station.DoesNotExist:
                return custom_response(
                    detail=f"'{station_number}' stansiyasi topilmadi",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
        
        # Get parameters
        parameters = Parameter.objects.filter(filters).order_by('datetime')
        
        # Check if parameters exist
        if not parameters.exists():
            return custom_response(
                detail="Berilgan parametrlar va vaqt davri uchun ma'lumotlar topilmadi",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Create DataFrame with parameters
        df = pd.DataFrame(list(parameters.values('datetime', 'value')))
        
        # Add UTC+5 time
        df['datetime_utc5'] = df['datetime'] + pd.Timedelta(hours=5)
        
        # Extract month from datetime
        df['month'] = df['datetime_utc5'].dt.month
        
        # Group by month and calculate statistics
        monthly_stats = []
        month_names = [
            'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
            'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'
        ]
        
        for month in range(1, 13):
            month_data = df[df['month'] == month]
            
            if len(month_data) > 0:
                values = month_data['value'].tolist()
                
                # Calculate mode
                month_mode = stats.mode(values)
                mode_values = [float(val) for val in month_mode.mode]
                
                monthly_stats.append({
                    'month': month,
                    'month_name': month_names[month - 1],
                    'mean': float(month_data['value'].mean()),
                    'median': float(month_data['value'].median()),
                    'mode': mode_values,
                    'min': float(month_data['value'].min()),
                    'max': float(month_data['value'].max()),
                    'std_dev': float(month_data['value'].std()) if len(month_data) > 1 else 0,
                    'count': len(month_data)
                })
            else:
                monthly_stats.append({
                    'month': month,
                    'month_name': month_names[month - 1],
                    'mean': None,
                    'median': None,
                    'mode': [],
                    'min': None,
                    'max': None,
                    'std_dev': None,
                    'count': 0
                })
        
        # Prepare response
        result = {
            'parameter': {
                'name': param_name.name,
                'slug': param_name.slug,
                'unit': param_name.unit
            },
            'year': year,
            'monthly_data': monthly_stats
        }
        
        # Add station information if provided
        if station:
            result['station'] = {
                'number': str(station.number),
                'name': station.name
            }
        else:
            result['station'] = None
        
        return custom_response(
            data=result,
            status_code=status.HTTP_200_OK
        )


class CorrelationView(APIView):
    """
    View for calculating correlation between parameters
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Statistics'],
        operation_description="Parametrlar orasidagi korrelyatsiyani hisoblash",
        manual_parameters=[
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Korrelyatsiya hisoblanadigan yil",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'station_number',
                openapi.IN_QUERY,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            ),
            # openapi.Parameter(
            #     'correlation_type',
            #     openapi.IN_QUERY,
            #     description="Korrelyatsiya turi (pearson, spearman, kendall)",
            #     type=openapi.TYPE_STRING,
            #     default="pearson",
            #     required=False
            # )
        ],
        responses={
            200: openapi.Response(
                description="Korrelyatsiya muvaffaqiyatli hisoblandi",
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
                                'year': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'period': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'start_date': openapi.Schema(type=openapi.TYPE_STRING),
                                        'end_date': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'correlation_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING)
                                ),
                                'correlation_matrix': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    additionalProperties=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        additionalProperties=openapi.Schema(type=openapi.TYPE_NUMBER)
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: f"Ruxsat mavjud emas: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: "Parametr nomlari yoki stansiya topilmadi",
        }
    )
    def get(self, request):
        try:
            # Get query parameters
            year_str = request.query_params.get('year')
            station_number = request.query_params.get('station_number')
            correlation_type = request.query_params.get('correlation_type', 'pearson').lower()
            
            # Validate correlation type
            if correlation_type not in ['pearson', 'spearman', 'kendall']:
                return custom_response(
                    detail="correlation_type 'pearson', 'spearman', yoki 'kendall' bo'lishi kerak",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Validate year parameter
            if not year_str:
                return custom_response(
                    detail="year parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
                
            # Validate station_number parameter
            if not station_number:
                return custom_response(
                    detail="station_number parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Parse year parameter
            try:
                year = int(year_str)
                start_date = datetime(year, 1, 1) - timedelta(hours=5)  # UTC+5 to UTC
                end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1) - timedelta(hours=5)  # UTC+5 to UTC
            except ValueError:
                return custom_response(
                    detail="year butun son bo'lishi kerak",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Get station
            try:
                station = Station.objects.get(number=station_number)
            except Station.DoesNotExist:
                return custom_response(
                    detail=f"'{station_number}' stansiyasi topilmadi",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Get all parameter names with data
            param_data = {}
            param_names = []
            
            # Get all parameter names for this station in the time range
            parameter_names = ParameterName.objects.filter(
                parameters__station=station,
                parameters__datetime__gte=start_date,
                parameters__datetime__lte=end_date
            ).distinct()
            
            # Check if we have enough parameters for correlation
            if parameter_names.count() < 2:
                return custom_response(
                    detail="Korrelyatsiyani hisoblash uchun kamida ikkita parametr kerak",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Get all parameters with their names as a single query
            all_parameters = Parameter.objects.filter(
                station=station,
                datetime__gte=start_date,
                datetime__lte=end_date
            ).select_related('parameter_name').values(
                'parameter_name__id', 
                'parameter_name__name', 
                'datetime', 
                'value'
            )
            
            # Group data by parameter
            for param in all_parameters:
                param_id = param['parameter_name__id']
                param_name = param['parameter_name__name']
                
                if param_id not in param_data:
                    param_data[param_id] = {
                        'name': param_name,
                        'data': []
                    }
                    param_names.append(param_name)
                
                param_data[param_id]['data'].append({
                    'datetime': param['datetime'],
                    'value': param['value']
                })
            
            # Convert to pandas DataFrames for efficient correlation calculation
            dfs = {}
            for param_id, data in param_data.items():
                df = pd.DataFrame(data['data'])
                if len(df) > 1:  # Only include parameters with multiple data points
                    dfs[data['name']] = df.set_index('datetime')
            
            # Check again if we have enough parameters
            if len(dfs) < 2:
                return custom_response(
                    detail="Korrelyatsiyani hisoblash uchun kamida ikkita parametr kerak",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Create a list of parameter names based on available dataframes
            param_names = list(dfs.keys())
            
            # Initialize correlation matrix
            correlation_matrix = {param: {p: None for p in param_names} for param in param_names}
            
            # Self-correlations are always 1
            for param in param_names:
                correlation_matrix[param][param] = 1.0
                
            # Calculate correlations between pairs
            for i, param1 in enumerate(param_names):
                for j, param2 in enumerate(param_names):
                    # Skip if already calculated or self-correlation
                    if i >= j:
                        continue
                    
                    # Merge the dataframes on datetime index
                    merged = pd.merge(
                        dfs[param1][['value']], 
                        dfs[param2][['value']], 
                        left_index=True,  
                        right_index=True,
                        suffixes=('_1', '_2')
                    )
                    
                    # Only calculate if we have enough matching data points
                    if len(merged) >= 2:
                        try:
                            if correlation_type == 'pearson':
                                corr = merged['value_1'].corr(merged['value_2'], method='pearson')
                            elif correlation_type == 'spearman':
                                corr = merged['value_1'].corr(merged['value_2'], method='spearman')
                            elif correlation_type == 'kendall':
                                corr = merged['value_1'].corr(merged['value_2'], method='kendall')
                            
                            # Round to 2 decimal places
                            if not pd.isna(corr):
                                correlation_matrix[param1][param2] = round(float(corr), 2)
                                correlation_matrix[param2][param1] = round(float(corr), 2)
                            else:
                                correlation_matrix[param1][param2] = 0
                                correlation_matrix[param2][param1] = 0
                        except:
                            correlation_matrix[param1][param2] = 0
                            correlation_matrix[param2][param1] = 0
                    else:
                        correlation_matrix[param1][param2] = 0
                        correlation_matrix[param2][param1] = 0
            
            # Prepare response
            result = {
                'year': year,
                'station': {
                    'number': str(station.number),
                    'name': station.name
                },
                'period': {
                    'start_date': (start_date + timedelta(hours=5)).isoformat(),
                    'end_date': (end_date + timedelta(hours=5)).isoformat()
                },
                'correlation_type': correlation_type,
                'parameters': param_names,
                'correlation_matrix': correlation_matrix
            }
            
            return custom_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            # Log the exception for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in CorrelationView: {str(e)}")
            
            return custom_response(
                detail=f"Korrelyatsiyani hisoblashda xatolik yuz berdi: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            )
