from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import AUTH_ERROR_MESSAGES
from ..models import Station, ParameterName, Parameter
from datetime import datetime, timedelta
from django.db.models import Avg, Min, Max, Q
from django.utils.dateparse import parse_datetime
import calendar
import pandas as pd


class ParameterChartView(APIView):
    """
    View for retrieving chart data for parameters for a specific station
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Charts'],
        operation_description="Parametrlar uchun grafik ma'lumotlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Vaqt oralig'i (day, month, year)",
                type=openapi.TYPE_STRING,
                enum=['day', 'month', 'year'],
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Sana (period=day uchun 'YYYY-MM-DD', period=month uchun 'YYYY-MM', period=year uchun 'YYYY')",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Grafik ma'lumotlari muvaffaqiyatli olindi",
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
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'x': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'y': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                ),
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'unit': openapi.Schema(type=openapi.TYPE_STRING),
                                'stations': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'param_value': openapi.Schema(
                                                type=openapi.TYPE_NUMBER,
                                                description="Dynamic field containing the parameter value. The key will be the parameter slug."
                                            )
                                        }
                                    )
                                ),
                                'parameter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'period': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya yoki parametr nomi topilmadi",
        }
    )
    def get(self, request, station_number):
        """Get chart data for a specific station"""
        # Validate and get parameter name
        parameter_slug = request.query_params.get('parameter_name')
        if not parameter_slug:
            return custom_response(
                detail="Parametr nomi kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        try:
            parameter_name = ParameterName.objects.get(slug=parameter_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Validate period
        period = request.query_params.get('period')
        if not period or period not in ['day', 'month', 'year']:
            return custom_response(
                detail="Noto'g'ri vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Validate date
        date_str = request.query_params.get('date')
        if not date_str:
            return custom_response(
                detail="Sana kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get the specified station
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Calculate date range based on period and date string
        try:
            date_range = self._calculate_date_range(period, date_str)
            if not date_range:
                return custom_response(
                    detail="Noto'g'ri sana formati",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            start_date, end_date = date_range
        except ValueError as e:
            return custom_response(
                detail=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get chart data based on period
        if period == 'day':
            chart_data = self._get_day_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'month':
            chart_data = self._get_month_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'year':
            chart_data = self._get_year_chart_data(station, parameter_name, start_date, end_date)
        else:
            # Should not reach here due to validation above
            return custom_response(
                detail="Noma'lum vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get all stations from the database
        all_stations = Station.objects.all()
        stations_list = []
        
        # For each station, find its highest parameter value or set to null if no data
        for station_obj in all_stations:
            station_data = {
                'number': station_obj.number,
                'name': station_obj.name
            }
            
            # Try to find parameter data for this station
            highest_param = Parameter.objects.filter(
                parameter_name=parameter_name,
                station=station_obj,
                datetime__gte=start_date,
                datetime__lte=end_date
            ).order_by('-value').first()
            
            # Add the parameter value with the parameter name as the key
            # Set to null if no data is found
            if highest_param and highest_param.value is not None:
                station_data[parameter_name.slug] = highest_param.value
            else:
                station_data[parameter_name.slug] = None
                
            stations_list.append(station_data)
        
        # Prepare response
        result = {
            'items': chart_data,
            'count': len(chart_data),
            'unit': parameter_name.unit,
            'stations': stations_list,
            'parameter': {
                'slug': parameter_name.slug,
                'name': parameter_name.name
            },
            'period': period
        }
        
        return custom_response(
            data=result,
            status_code=status.HTTP_200_OK
        )
    
    def _calculate_date_range(self, period, date_str):
        """
        Calculate date range based on period and date string
        
        Args:
            period (str): The period (day, month, year)
            date_str (str): The date string
            
        Returns:
            tuple: (start_date, end_date) in UTC
        """
        if period == 'day':
            try:
                # Expect format YYYY-MM-DD
                date = datetime.strptime(date_str, '%Y-%m-%d')
                start_date = datetime(date.year, date.month, date.day, 0, 0, 0)
                end_date = datetime(date.year, date.month, date.day, 23, 59, 59)
            except ValueError:
                return None
        elif period == 'month':
            try:
                # Expect format YYYY-MM
                date = datetime.strptime(date_str, '%Y-%m')
                start_date = datetime(date.year, date.month, 1, 0, 0, 0)
                
                # Get last day of month
                _, last_day = calendar.monthrange(date.year, date.month)
                end_date = datetime(date.year, date.month, last_day, 23, 59, 59)
            except ValueError:
                return None
        elif period == 'year':
            try:
                # Expect format YYYY
                year = int(date_str)
                start_date = datetime(year, 1, 1, 0, 0, 0)
                end_date = datetime(year, 12, 31, 23, 59, 59)
            except ValueError:
                return None
        else:
            return None
        
        # Convert from UTC+5 to UTC by subtracting 5 hours
        start_date = start_date - timedelta(hours=5)
        end_date = end_date - timedelta(hours=5)
        
        return start_date, end_date
    
    def _get_day_chart_data(self, station, parameter_name, start_date, end_date):
        """
        Get hourly chart data for a day
        
        Args:
            station (Station or str): The station, None for average, or 'all' for all stations
            parameter_name (ParameterName): The parameter name
            start_date (datetime): Start date in UTC
            end_date (datetime): End date in UTC
            
        Returns:
            list: Chart data items
        """
        # Build filter
        filters = Q(parameter_name=parameter_name)
        filters &= Q(datetime__gte=start_date)
        filters &= Q(datetime__lte=end_date)
        
        # Apply station filter only if it's a specific station
        if station and station != 'all':
            filters &= Q(station=station)
        
        # Get parameters
        parameters = Parameter.objects.filter(filters).order_by('datetime')
        
        # Process into chart data
        chart_data = []
        
        # Handle different cases based on station parameter
        if station == 'all':
            # Get all stations, including those with no data for this period
            all_stations = Station.objects.all()
            
            # Create a lookup for station names
            station_lookup = {s.id: s.name for s in all_stations}
            
            # Process each station separately
            for station_id, station_name in station_lookup.items():
                # Filter parameters for this station
                station_params = parameters.filter(station_id=station_id)
                
                # Convert to pandas DataFrame for easier processing
                data = []
                for param in station_params:
                    # Skip parameters with None values
                    if param.value is None:
                        continue
                        
                    # Convert datetime from UTC to UTC+5 by adding 5 hours
                    local_datetime = param.datetime + timedelta(hours=5)
                    
                    data.append({
                        'datetime': local_datetime,
                        'datetime_hour': local_datetime.replace(minute=0, second=0, microsecond=0),
                        'value': param.value
                    })
                
                # If no data for this station, skip to next station
                if not data:
                    continue
                
                # Create DataFrame
                df = pd.DataFrame(data)
                
                # Group by hour
                grouped = df.groupby('datetime_hour').agg({
                    'value': 'mean',
                    'datetime': 'first'  # Keep first datetime for reference
                })
                
                # Reset index
                grouped = grouped.reset_index()
                
                # Process into chart data
                for _, row in grouped.iterrows():
                    # Format time for y-axis
                    time_str = row['datetime_hour'].strftime('%H:%M')
                    
                    chart_data.append({
                        'name': f"{station_name}",
                        'x': round(row['value'], 2),
                        'y': time_str
                    })
        
        elif station is None:
            # Handle 'avg' case (station is None)
            # Convert to pandas DataFrame for easier processing
            data = []
            for param in parameters:
                # Skip parameters with None values
                if param.value is None:
                    continue
                    
                # Convert datetime from UTC to UTC+5 by adding 5 hours
                local_datetime = param.datetime + timedelta(hours=5)
                
                data.append({
                    'datetime': local_datetime,
                    'datetime_hour': local_datetime.replace(minute=0, second=0, microsecond=0),
                    'value': param.value
                })
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Skip processing if DataFrame is empty
            if df.empty:
                return chart_data
            
            # Group by hour and calculate average
            grouped = df.groupby('datetime_hour').agg({
                'value': 'mean',
                'datetime': 'first'  # Keep first datetime for reference
            })
            
            # Reset index to make datetime_hour a column
            grouped = grouped.reset_index()
            
            # Process into chart data
            for _, row in grouped.iterrows():
                # Format time for y-axis
                time_str = row['datetime_hour'].strftime('%H:%M')
                
                chart_data.append({
                    'name': parameter_name.name,
                    'x': round(row['value'], 2),
                    'y': time_str
                })
        else:
            # Single station case - just process each parameter
            data = []
            for param in parameters:
                # Skip parameters with None values
                if param.value is None:
                    continue
                    
                # Convert datetime from UTC to UTC+5 by adding 5 hours
                local_datetime = param.datetime + timedelta(hours=5)
                
                data.append({
                    'datetime': local_datetime,
                    'datetime_hour': local_datetime.replace(minute=0, second=0, microsecond=0),
                    'value': param.value
                })
            
            # If no data for this station, skip it
            if not data:
                return chart_data
            
            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Group by hour
            grouped = df.groupby('datetime_hour').agg({
                'value': 'mean',
                'datetime': 'first'  # Keep first datetime for reference
            })
            
            # Reset index
            grouped = grouped.reset_index()
            
            # Process into chart data
            for _, row in grouped.iterrows():
                # Format time for y-axis
                time_str = row['datetime_hour'].strftime('%H:%M')
                
                chart_data.append({
                    'name': parameter_name.name,
                    'x': round(row['value'], 2),
                    'y': time_str
                })
        
        return chart_data
    
    def _get_month_chart_data(self, station, parameter_name, start_date, end_date):
        """
        Get daily min, max, avg chart data for a month
        
        Args:
            station (Station or str): The station, None for average, or 'all' for all stations
            parameter_name (ParameterName): The parameter name
            start_date (datetime): Start date in UTC
            end_date (datetime): End date in UTC
            
        Returns:
            list: Chart data items
        """
        # Build filter
        filters = Q(parameter_name=parameter_name)
        filters &= Q(datetime__gte=start_date)
        filters &= Q(datetime__lte=end_date)
        
        # Apply station filter only if it's a specific station
        if station and station != 'all':
            filters &= Q(station=station)
        
        # Get all parameters for the date range
        parameters = Parameter.objects.filter(filters).order_by('datetime')
        
        # Process into chart data based on station parameter
        chart_data = []
        
        if station == 'all':
            # Get all stations, including those with no data for this period
            all_stations = Station.objects.all()
            
            # Create a lookup for station names
            station_lookup = {s.id: s.name for s in all_stations}
            
            # Process each station separately
            for station_id, station_name in station_lookup.items():
                # Filter parameters for this station
                station_params = parameters.filter(station_id=station_id)
                
                # Convert to pandas DataFrame for easier processing
                data = []
                for param in station_params:
                    # Skip parameters with None values
                    if param.value is None:
                        continue
                    
                    # Convert datetime from UTC to UTC+5 by adding 5 hours
                    local_datetime = param.datetime + timedelta(hours=5)
                    
                    # Create date column (without time) for grouping
                    date_only = local_datetime.date()
                    
                    data.append({
                        'datetime': local_datetime,
                        'date': date_only,
                        'value': param.value
                    })
                
                # If no data for this station, skip to next station
                if not data:
                    continue
                
                # Create DataFrame
                df = pd.DataFrame(data)
                
                # Group by date and calculate min, max, and avg
                grouped = df.groupby('date').agg({
                    'value': ['min', 'max', 'mean'],
                    'datetime': 'first'  # Keep first datetime for reference
                })
                
                # Flatten column names
                grouped.columns = ['min', 'max', 'avg', 'datetime']
                
                # Reset index
                grouped = grouped.reset_index()
                
                # Process into chart data
                for _, row in grouped.iterrows():
                    # Format date for y-axis
                    date_str = row['date'].strftime('%d/%m')
                    
                    # Add min value
                    chart_data.append({
                        'name': f"min {station_name}",
                        'x': row['min'],
                        'y': date_str
                    })
                    
                    # Add max value
                    chart_data.append({
                        'name': f"max {station_name}",
                        'x': row['max'],
                        'y': date_str
                    })
                    
                    # Add avg value
                    chart_data.append({
                        'name': f"avg {station_name}",
                        'x': round(row['avg'], 2),
                        'y': date_str
                    })
        else:
            # Convert to pandas DataFrame for easier processing
            data = []
            for param in parameters:
                # Convert datetime from UTC to UTC+5 by adding 5 hours
                local_datetime = param.datetime + timedelta(hours=5)
                
                # Create date column (without time) for grouping
                date_only = local_datetime.date()
                
                data.append({
                    'datetime': local_datetime,
                    'date': date_only,
                    'value': param.value
                })
            
            # If no data, skip it
            if not data:
                return chart_data
            
            df = pd.DataFrame(data)
            
            # Group by date and calculate min, max, avg
            grouped = df.groupby('date').agg({
                'value': ['min', 'max', 'mean'],
                'datetime': 'first'  # Keep first datetime for reference
            })
            
            # Flatten column names
            grouped.columns = ['min', 'max', 'avg', 'datetime']
            
            # Reset index to make date a column
            grouped = grouped.reset_index()
            
            # Process into chart data
            for _, row in grouped.iterrows():
                # Format date for y-axis
                date_str = row['date'].strftime('%d/%m')
                
                # Add min value
                chart_data.append({
                    'name': f"min {parameter_name.name}",
                    'x': row['min'],
                    'y': date_str
                })
                
                # Add max value
                chart_data.append({
                    'name': f"max {parameter_name.name}",
                    'x': row['max'],
                    'y': date_str
                })
                
                # Add avg value
                chart_data.append({
                    'name': f"avg {parameter_name.name}",
                    'x': round(row['avg'], 2),
                    'y': date_str
                })
        
        return chart_data
    
    def _get_year_chart_data(self, station, parameter_name, start_date, end_date):
        """
        Get monthly min, max, avg chart data for a year
        
        Args:
            station (Station or str): The station, None for average, or 'all' for all stations
            parameter_name (ParameterName): The parameter name
            start_date (datetime): Start date in UTC
            end_date (datetime): End date in UTC
            
        Returns:
            list: Chart data items
        """
        # Build filter
        filters = Q(parameter_name=parameter_name)
        filters &= Q(datetime__gte=start_date)
        filters &= Q(datetime__lte=end_date)
        
        # Apply station filter only if it's a specific station
        if station and station != 'all':
            filters &= Q(station=station)
        
        # Get all parameters for the date range
        parameters = Parameter.objects.filter(filters).order_by('datetime')
        
        # Process into chart data based on station parameter
        chart_data = []
        
        if station == 'all':
            # Get all stations, including those with no data for this period
            all_stations = Station.objects.all()
            
            # Create a lookup for station names
            station_lookup = {s.id: s.name for s in all_stations}
            
            # Process each station separately
            for station_id, station_name in station_lookup.items():
                # Filter parameters for this station
                station_params = parameters.filter(station_id=station_id)
                
                # Convert to pandas DataFrame for easier processing
                data = []
                for param in station_params:
                    # Skip parameters with None values
                    if param.value is None:
                        continue
                    
                    # Convert datetime from UTC to UTC+5 by adding 5 hours
                    local_datetime = param.datetime + timedelta(hours=5)
                    
                    # Create year-month column for grouping
                    year_month = local_datetime.strftime('%Y-%m')
                    
                    data.append({
                        'datetime': local_datetime,
                        'year_month': year_month,
                        'month': local_datetime.month,  # Keep month for sorting
                        'value': param.value
                    })
                
                # If no data for this station, skip to next station
                if not data:
                    continue
                
                # Create DataFrame
                df = pd.DataFrame(data)
                
                # Group by year-month and calculate min, max, and avg
                grouped = df.groupby(['year_month', 'month']).agg({
                    'value': ['min', 'max', 'mean'],
                    'datetime': 'first'  # Keep first datetime for reference
                })
                
                # Flatten column names
                grouped.columns = ['min', 'max', 'avg', 'datetime']
                
                # Reset index
                grouped = grouped.reset_index()
                
                # Sort by month
                grouped = grouped.sort_values('month')
                
                # Process into chart data
                for _, row in grouped.iterrows():
                    # Format month for y-axis
                    month_str = row['datetime'].strftime('%b')
                    
                    # Add min value
                    chart_data.append({
                        'name': f"min {station_name}",
                        'x': row['min'],
                        'y': month_str
                    })
                    
                    # Add max value
                    chart_data.append({
                        'name': f"max {station_name}",
                        'x': row['max'],
                        'y': month_str
                    })
                    
                    # Add avg value
                    chart_data.append({
                        'name': f"avg {station_name}",
                        'x': round(row['avg'], 2),
                        'y': month_str
                    })
        else:
            # Convert to pandas DataFrame for easier processing
            data = []
            for param in parameters:
                # Convert datetime from UTC to UTC+5 by adding 5 hours
                local_datetime = param.datetime + timedelta(hours=5)
                
                # Create year-month column for grouping
                year_month = local_datetime.strftime('%Y-%m')
                
                data.append({
                    'datetime': local_datetime,
                    'year_month': year_month,
                    'month': local_datetime.month,  # Keep month for sorting
                    'value': param.value
                })
            
            # If no data, skip it
            if not data:
                return chart_data
            
            df = pd.DataFrame(data)
            
            # Group by year-month and calculate min, max, avg
            grouped = df.groupby('year_month').agg({
                'value': ['min', 'max', 'mean'],
                'datetime': 'first',  # Keep first datetime for reference
                'month': 'first'      # Keep month for reference
            })
            
            # Flatten column names
            grouped.columns = ['min', 'max', 'avg', 'datetime', 'month']
            
            # Reset index to make year_month a column
            grouped = grouped.reset_index()
            
            # Sort by month
            grouped = grouped.sort_values('month')
            
            # Process into chart data
            for _, row in grouped.iterrows():
                # Format month for y-axis (e.g., "Jan", "Feb", etc.)
                month_str = row['datetime'].strftime('%b')
                
                # Add min value
                chart_data.append({
                    'name': f"min {parameter_name.name}",
                    'x': row['min'],
                    'y': month_str
                })
                
                # Add max value
                chart_data.append({
                    'name': f"max {parameter_name.name}",
                    'x': row['max'],
                    'y': month_str
                })
                
                # Add avg value
                chart_data.append({
                    'name': f"avg {parameter_name.name}",
                    'x': round(row['avg'], 2),
                    'y': month_str
                })
        
        return chart_data


class ParameterAvgChartView(ParameterChartView):
    """
    View for retrieving chart data with average values across all stations
    """
    
    @swagger_auto_schema(
        tags=['Charts'],
        operation_description="Barcha stansiyalar bo'yicha o'rtacha parametrlar uchun grafik ma'lumotlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Vaqt oralig'i (day, month, year)",
                type=openapi.TYPE_STRING,
                enum=['day', 'month', 'year'],
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Sana (period=day uchun 'YYYY-MM-DD', period=month uchun 'YYYY-MM', period=year uchun 'YYYY')",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Grafik ma'lumotlari muvaffaqiyatli olindi",
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
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'x': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'y': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                ),
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'unit': openapi.Schema(type=openapi.TYPE_STRING),
                                'stations': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'param_value': openapi.Schema(
                                                type=openapi.TYPE_NUMBER,
                                                description="Dynamic field containing the parameter value. The key will be the parameter slug."
                                            )
                                        }
                                    )
                                ),
                                'parameter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'period': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Parametr nomi topilmadi",
        }
    )
    def get(self, request):
        """Get chart data with average values across all stations"""
        # Validate and get parameter name
        parameter_slug = request.query_params.get('parameter_name')
        if not parameter_slug:
            return custom_response(
                detail="Parametr nomi kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        try:
            parameter_name = ParameterName.objects.get(slug=parameter_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Validate period
        period = request.query_params.get('period')
        if not period or period not in ['day', 'month', 'year']:
            return custom_response(
                detail="Noto'g'ri vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Validate date
        date_str = request.query_params.get('date')
        if not date_str:
            return custom_response(
                detail="Sana kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Use None for station to represent average of all stations
        station = None
        
        # Calculate date range based on period and date string
        try:
            date_range = self._calculate_date_range(period, date_str)
            if not date_range:
                return custom_response(
                    detail="Noto'g'ri sana formati",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            start_date, end_date = date_range
        except ValueError as e:
            return custom_response(
                detail=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get chart data based on period
        if period == 'day':
            chart_data = self._get_day_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'month':
            chart_data = self._get_month_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'year':
            chart_data = self._get_year_chart_data(station, parameter_name, start_date, end_date)
        else:
            # Should not reach here due to validation above
            return custom_response(
                detail="Noma'lum vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get all stations from the database instead of filtering by parameter data
        all_stations = Station.objects.all()
        stations_list = []
        
        # For each station, find its highest parameter value or set to null if no data
        for station_obj in all_stations:
            station_data = {
                'number': station_obj.number,
                'name': station_obj.name
            }
            
            # Try to find parameter data for this station
            highest_param = Parameter.objects.filter(
                parameter_name=parameter_name,
                station=station_obj,
                datetime__gte=start_date,
                datetime__lte=end_date
            ).order_by('-value').first()
            
            # Add the parameter value with the parameter name as the key
            # Set to null if no data is found
            if highest_param and highest_param.value is not None:
                station_data[parameter_name.slug] = highest_param.value
            else:
                station_data[parameter_name.slug] = None
                
            stations_list.append(station_data)
        
        # Prepare response
        result = {
            'items': chart_data,
            'count': len(chart_data),
            'unit': parameter_name.unit,
            'stations': stations_list,
            'parameter': {
                'slug': parameter_name.slug,
                'name': parameter_name.name
            },
            'period': period
        }
        
        return custom_response(
            data=result,
            status_code=status.HTTP_200_OK
        )


class ParameterAllChartView(ParameterChartView):
    """
    View for retrieving chart data for all stations individually
    """
    
    @swagger_auto_schema(
        tags=['Charts'],
        operation_description="Barcha stansiyalar uchun alohida parametrlar grafik ma'lumotlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'parameter_name',
                openapi.IN_QUERY,
                description="Parametr nomi slugi",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'period',
                openapi.IN_QUERY,
                description="Vaqt oralig'i (day, month, year)",
                type=openapi.TYPE_STRING,
                enum=['day', 'month', 'year'],
                required=True
            ),
            openapi.Parameter(
                'date',
                openapi.IN_QUERY,
                description="Sana (period=day uchun 'YYYY-MM-DD', period=month uchun 'YYYY-MM', period=year uchun 'YYYY')",
                type=openapi.TYPE_STRING,
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Grafik ma'lumotlari muvaffaqiyatli olindi",
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
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'x': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'y': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                ),
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'unit': openapi.Schema(type=openapi.TYPE_STRING),
                                'stations': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'param_value': openapi.Schema(
                                                type=openapi.TYPE_NUMBER,
                                                description="Dynamic field containing the parameter value. The key will be the parameter slug."
                                            )
                                        }
                                    )
                                ),
                                'parameter': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'period': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "So'rov parametrlari noto'g'ri",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Parametr nomi topilmadi",
        }
    )
    def get(self, request):
        """Get chart data for all stations individually"""
        # Validate and get parameter name
        parameter_slug = request.query_params.get('parameter_name')
        if not parameter_slug:
            return custom_response(
                detail="Parametr nomi kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        try:
            parameter_name = ParameterName.objects.get(slug=parameter_slug)
        except ParameterName.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr nomi"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Validate period
        period = request.query_params.get('period')
        if not period or period not in ['day', 'month', 'year']:
            return custom_response(
                detail="Noto'g'ri vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Validate date
        date_str = request.query_params.get('date')
        if not date_str:
            return custom_response(
                detail="Sana kiritilmagan",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Use 'all' as a special identifier for all stations
        station = 'all'
        
        # Calculate date range based on period and date string
        try:
            date_range = self._calculate_date_range(period, date_str)
            if not date_range:
                return custom_response(
                    detail="Noto'g'ri sana formati",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
            start_date, end_date = date_range
        except ValueError as e:
            return custom_response(
                detail=str(e),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get chart data based on period
        if period == 'day':
            chart_data = self._get_day_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'month':
            chart_data = self._get_month_chart_data(station, parameter_name, start_date, end_date)
        elif period == 'year':
            chart_data = self._get_year_chart_data(station, parameter_name, start_date, end_date)
        else:
            # Should not reach here due to validation above
            return custom_response(
                detail="Noma'lum vaqt oralig'i",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Get all stations from the database instead of filtering by parameter data
        all_stations = Station.objects.all()
        stations_list = []
        
        # For each station, find its highest parameter value or set to null if no data
        for station_obj in all_stations:
            station_data = {
                'number': station_obj.number,
                'name': station_obj.name
            }
            
            # Try to find parameter data for this station
            highest_param = Parameter.objects.filter(
                parameter_name=parameter_name,
                station=station_obj,
                datetime__gte=start_date,
                datetime__lte=end_date
            ).order_by('-value').first()
            
            # Add the parameter value with the parameter name as the key
            # Set to null if no data is found
            if highest_param and highest_param.value is not None:
                station_data[parameter_name.slug] = highest_param.value
            else:
                station_data[parameter_name.slug] = None
                
            stations_list.append(station_data)
        
        # Prepare response
        result = {
            'items': chart_data,
            'count': len(chart_data),
            'unit': parameter_name.unit,
            'stations': stations_list,
            'parameter': {
                'slug': parameter_name.slug,
                'name': parameter_name.name
            },
            'period': period
        }
        
        return custom_response(
            data=result,
            status_code=status.HTTP_200_OK
        )

