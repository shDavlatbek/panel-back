from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db.models import Avg, Min, Max, StdDev, Count, Q
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta, timezone
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
                description="Statistika hisoblanadigan yil",
                type=openapi.TYPE_INTEGER,
                required=True
            ),
            openapi.Parameter(
                'station_number',
                openapi.IN_QUERY,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
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
                                'year': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'summary': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'mean': openapi.Schema(type=openapi.TYPE_STRING),
                                        'median': openapi.Schema(type=openapi.TYPE_STRING),
                                        'std_dev': openapi.Schema(type=openapi.TYPE_STRING),
                                        'coefficient_of_variation': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'trend': openapi.Schema(type=openapi.TYPE_STRING)
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
                                ),
                                'items': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'x': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'y': openapi.Schema(type=openapi.TYPE_STRING)
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
        try:
            # Get query parameters
            param_name_slug = request.query_params.get('parameter_name')
            year_str = request.query_params.get('year')
            station_number = request.query_params.get('station_number')
            
            # Validate parameter_name
            if not param_name_slug:
                return custom_response(
                    detail="parameter_name parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
                
            # Validate year
            if not year_str:
                return custom_response(
                    detail="year parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Validate station_number
            if not station_number:
                return custom_response(
                    detail="station_number parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
                
            # Process the date range based on parameters
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
            
            # Get station
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
            
            # Helper function to handle non-JSON-compliant float values
            def safe_float(value):
                if value is None:
                    return None
                try:
                    float_val = float(value)
                    if np.isnan(float_val) or np.isinf(float_val):
                        return None
                    return float_val
                except:
                    return None
            
            # Handle rainfall parameter specially - filter out -1 values which represent missing data
            is_rainfall = param_name_slug == 'rainfall'
            
            # Get values based on parameter type
            if is_rainfall:
                # For rainfall, exclude -1 values (missing data)
                values = list(parameters.filter(value__gt=-1).values_list('value', flat=True))
                # Get all parameters even with -1 for DataFrame (we'll filter later)
                all_values = list(parameters.values_list('value', flat=True))
                all_datetimes = list(parameters.values_list('datetime', flat=True))
                values_df = pd.DataFrame({
                    'value': all_values,
                    'datetime': all_datetimes
                })
                # Filter out -1 values for calculations
                values_df = values_df[values_df['value'] > -1]
            else:
                # For other parameters, use all values
                values = list(parameters.values_list('value', flat=True))
                values_df = pd.DataFrame({
                    'value': values,
                    'datetime': list(parameters.values_list('datetime', flat=True))
                })
            
            # Check if filtered values exist (especially important for rainfall)
            if not values:
                return custom_response(
                    detail="Berilgan parametrlar va vaqt davri uchun ma'lumotlar topilmadi",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Calculate mode (safely)
            try:
                mode_result = stats.mode(values)
                # Handle different SciPy versions
                if hasattr(mode_result, 'mode'):
                    if isinstance(mode_result.mode, np.ndarray):
                        mode_values = [safe_float(m) for m in mode_result.mode]
                    else:
                        mode_values = [safe_float(mode_result.mode)]
                else:
                    # For newer SciPy versions where mode returns a single value
                    mode_values = [safe_float(mode_result)]
            except Exception:
                # Fallback if mode calculation fails
                mode_values = [safe_float(values[0])] if values else [None]
            
            # Calculate mean, median, standard deviation, and coefficient of variation
            if is_rainfall:
                # For rainfall, calculate from filtered values
                try:
                    mean_val = safe_float(np.mean(values)) if values else None
                    median_val = safe_float(np.median(values)) if values else None
                    std_dev_val = safe_float(np.std(values)) if len(values) > 1 else None
                except:
                    mean_val = None
                    median_val = None
                    std_dev_val = None
            else:
                # For other parameters, use Django's aggregate functions
                try:
                    mean_val = safe_float(parameters.aggregate(Avg('value'))['value__avg'])
                    median_val = safe_float(np.median(values))
                    std_dev_val = safe_float(parameters.aggregate(StdDev('value'))['value__stddev'] or 0)
                except:
                    mean_val = None
                    median_val = None
                    std_dev_val = None
            
            try:
                coef_var = safe_float(std_dev_val / mean_val) if mean_val and mean_val != 0 else None
            except:
                coef_var = None
            
            # Calculate trend (Kendall's Tau) - safely
            try:
                from scipy.stats import kendalltau
                x = range(len(values))
                tau, p_value = kendalltau(x, values)
                tau = safe_float(tau)
                p_value = safe_float(p_value)
                trend_direction = "O'sayotgan ↑" if tau and tau > 0 else "Pasayuvchi ↓" if tau and tau < 0 else "Stabil"
            except Exception:
                # Fallback if trend calculation fails
                trend_direction = "Stabil"
                tau = None
                p_value = None
            
            # Format summary values with appropriate units and precision
            unit = param_name.unit or ""
            summary = {
                'mean': f"{round(mean_val, 1)} {unit}" if mean_val is not None else None,
                'median': f"{round(median_val, 1)} {unit}" if median_val is not None else None,
                'std_dev': f"{round(std_dev_val, 1)} {unit}" if std_dev_val is not None else None,
                'coefficient_of_variation': round(coef_var, 2) if coef_var is not None else None,
                'trend': trend_direction,
                'tau': tau,
                'p_value': p_value
            }
            
            # Get min/max for statistics
            if is_rainfall:
                try:
                    min_val = safe_float(min(values)) if values else None
                    max_val = safe_float(max(values)) if values else None
                    variance = safe_float(np.var(values)) if len(values) > 1 else None
                    count = len(values)
                except:
                    min_val = None
                    max_val = None
                    variance = None
                    count = 0
            else:
                try:
                    min_val = safe_float(parameters.aggregate(Min('value'))['value__min'])
                    max_val = safe_float(parameters.aggregate(Max('value'))['value__max'])
                    variance = safe_float(np.var(values))
                    count = parameters.count()
                except:
                    min_val = None
                    max_val = None
                    variance = None
                    count = 0
            
            # Convert data for detailed statistics
            stats_data = {
                'mean': mean_val,
                'min': min_val,
                'max': max_val,
                'std_dev': std_dev_val,
                'count': count,
                'median': median_val,
                'mode': mode_values,
                'variance': variance,
                'coefficient_of_variation': coef_var,
            }
            
            # Add UTC+5 time
            values_df['datetime_utc5'] = values_df['datetime'] + pd.Timedelta(hours=5)
            
            # Extract month and year from datetime
            values_df['month'] = values_df['datetime_utc5'].dt.month
            values_df['year'] = values_df['datetime_utc5'].dt.year
            
            # Use the selected year
            year_data = values_df[values_df['year'] == selected_year]
            
            # Initialize monthly data
            monthly_mode = []
            month_names = [
                'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
                'Iyul', 'Avgust', 'Sentabr', 'Oktabr', 'Noyabr', 'Dekabr'
            ]
            
            # Short month names for chart
            short_month_names = [
                'Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn',
                'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'
            ]
            
            # Prepare chart items
            chart_items = []
            
            # Calculate monthly statistics
            for month in range(1, 13):
                month_data = year_data[year_data['month'] == month]
                
                if len(month_data) > 0:
                    month_values = month_data['value'].tolist()
                    
                    # Calculate mode safely
                    try:
                        month_mode = stats.mode(month_values)
                        # Handle different SciPy versions
                        if hasattr(month_mode, 'mode'):
                            if isinstance(month_mode.mode, np.ndarray):
                                month_mode_values = [safe_float(m) for m in month_mode.mode]
                            else:
                                month_mode_values = [safe_float(month_mode.mode)]
                        else:
                            # For newer SciPy versions where mode returns a single value
                            month_mode_values = [safe_float(month_mode)]
                    except Exception:
                        # Fallback if mode calculation fails
                        month_mode_values = [safe_float(month_values[0])] if month_values else [None]
                    
                    # Calculate average safely
                    try:
                        month_avg = safe_float(month_data['value'].mean())
                    except Exception:
                        month_avg = None
                    
                    monthly_mode.append({
                        'month': month,
                        'month_name': month_names[month - 1],
                        'mode': month_mode_values,
                        'count': len(month_data)
                    })
                    
                    # Add to chart items
                    chart_items.append({
                        'name': param_name.name,
                        'x': round(month_avg, 1) if month_avg is not None else None,
                        'y': short_month_names[month - 1]
                    })
                else:
                    monthly_mode.append({
                        'month': month,
                        'month_name': month_names[month - 1],
                        'mode': [],
                        'count': 0
                    })
                    
                    # Add null values for missing months
                    chart_items.append({
                        'name': param_name.name,
                        'x': None,
                        'y': short_month_names[month - 1]
                    })
            
            # Prepare response
            result = {
                'parameter': {
                    'name': param_name.name,
                    'slug': param_name.slug,
                    'unit': param_name.unit
                },
                'year': selected_year,
                'summary': summary,
                'statistics': stats_data,
                'monthly_mode': monthly_mode,
                'items': chart_items
            }
            
            # Add station information
            result['station'] = {
                'number': str(station.number),
                'name': station.name
            }
            
            return custom_response(
                data=result,
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            # Log the exception for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in StatisticsView: {str(e)}")
            
            return custom_response(
                detail=f"Statistikani hisoblashda xatolik yuz berdi: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
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
                                'correlation_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    additionalProperties=openapi.Schema(type=openapi.TYPE_STRING)
                                ),
                                'items': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
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
                'parameter_name__slug',
                'datetime', 
                'value'
            )
            
            # Group data by parameter
            for param in all_parameters:
                param_id = param['parameter_name__id']
                param_name = param['parameter_name__name']
                param_slug = param['parameter_name__slug']
                
                if param_id not in param_data:
                    param_data[param_id] = {
                        'name': param_name,
                        'slug': param_slug,
                        'data': []
                    }
                    param_names.append(param_name)
                
                param_data[param_id]['data'].append({
                    'datetime': param['datetime'],
                    'value': param['value']
                })
            
            # Convert to pandas DataFrames for efficient correlation calculation
            dfs = {}
            param_map = {}  # Map to store slug:name pairs
            
            for param_id, data in param_data.items():
                df = pd.DataFrame(data['data'])
                if len(df) > 1:  # Only include parameters with multiple data points
                    dfs[data['slug']] = df.set_index('datetime')
                    param_map[data['slug']] = data['name']
            
            # Check again if we have enough parameters
            if len(dfs) < 2:
                return custom_response(
                    detail="Korrelyatsiyani hisoblash uchun kamida ikkita parametr kerak",
                    status_code=status.HTTP_404_NOT_FOUND,
                    success=False
                )
            
            # Create a list of parameter slugs based on available dataframes
            param_slugs = list(dfs.keys())
            
            # Initialize correlation dict to store results
            correlation_result = []
            
            # Calculate correlations between pairs
            for param1 in param_slugs:
                param_result = {'parameter_name': param_map[param1]}
                
                # Self-correlation is always 1
                param_result[param1] = 1.0
                
                for param2 in param_slugs:
                    if param1 == param2:
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
                                param_result[param2] = round(float(corr), 2)
                            else:
                                param_result[param2] = 0
                        except:
                            param_result[param2] = 0
                    else:
                        param_result[param2] = 0
                
                correlation_result.append(param_result)
            
            # Prepare response
            result = {
                'year': year,
                'station': {
                    'number': str(station.number),
                    'name': station.name
                },
                'correlation_type': correlation_type,
                'parameters': param_map,
                'items': correlation_result
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


class ModeStatsView(APIView):
    """
    View for retrieving mode statistics for parameters by month
    """
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        tags=['Statistics'],
        # operation_summary="Parametrlar uchun oylik moda qiymatlarini olish",
        # operation_description="Ma'lum parametr uchun oylik moda qiymatlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'year',
                openapi.IN_QUERY,
                description="Moda statistikasi hisoblanadigan yil",
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
        ],
        responses={
            200: openapi.Response(
                description="Moda statistikasi muvaffaqiyatli olindi",
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
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'x': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'y': openapi.Schema(type=openapi.TYPE_STRING)
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
        try:
            # Get query parameters
            param_name_slug = request.query_params.get('parameter_name')
            year_str = request.query_params.get('year')
            station_number = request.query_params.get('station_number')
            
            # Validate parameter_name
            if not param_name_slug:
                return custom_response(
                    detail="parameter_name parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
                
            # Validate year
            if not year_str:
                return custom_response(
                    detail="year parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            
            # Validate station_number
            if not station_number:
                return custom_response(
                    detail="station_number parametri talab qilinadi",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
                
            # Process the date range based on parameters
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
            
            # Get station
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
            
            # Create a DataFrame for processing
            values_df = pd.DataFrame({
                'value': list(parameters.values_list('value', flat=True)),
                'datetime': list(parameters.values_list('datetime', flat=True))
            })
            
            # Add UTC+5 time
            values_df['datetime_utc5'] = values_df['datetime'] + pd.Timedelta(hours=5)
            
            # Extract month and year from datetime
            values_df['month'] = values_df['datetime_utc5'].dt.month
            values_df['year'] = values_df['datetime_utc5'].dt.year
            
            # Filter for the selected year
            year_data = values_df[values_df['year'] == selected_year]
            
            # Define month names (short versions for chart)
            short_month_names = [
                'Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn',
                'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek'
            ]
            
            # Initialize chart items array
            chart_items = []
            
            # Calculate mode for each month
            for month in range(1, 13):
                month_data = year_data[year_data['month'] == month]
                
                if len(month_data) > 0:
                    month_values = month_data['value'].tolist()
                    
                    # Calculate mode safely
                    try:
                        month_mode = stats.mode(month_values)
                        # Handle different SciPy versions
                        if hasattr(month_mode, 'mode'):
                            if isinstance(month_mode.mode, np.ndarray):
                                mode_value = float(month_mode.mode[0])
                            else:
                                mode_value = float(month_mode.mode)
                        else:
                            # For newer SciPy versions where mode returns a single value
                            mode_value = float(month_mode)
                    except Exception:
                        # Fallback if mode calculation fails
                        mode_value = float(month_values[0]) if month_values else 0.0
                    
                    # Add to chart items
                    chart_items.append({
                        'name': param_name.name,
                        'x': round(mode_value, 1),
                        'y': short_month_names[month - 1]
                    })
            
            # Sort by month order
            month_order = {name: idx for idx, name in enumerate(short_month_names)}
            chart_items.sort(key=lambda x: month_order[x['y']])
            
            return custom_response(
                data={
                    'items': chart_items
                },
                status_code=status.HTTP_200_OK
            )
        except Exception as e:
            # Log the exception for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in ModeStatsView: {str(e)}")
            
            return custom_response(
                detail=f"Moda statistikasini hisoblashda xatolik yuz berdi: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            )
