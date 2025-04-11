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
    
    @swagger_auto_schema(
        tags=['Parameters'],
        operation_description="Parametrlarni veb-saytdan olish va ma'lumotlar bazasiga saqlash",
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     required=None,
        #     properties={
        #         'station_numbers': openapi.Schema(
        #             type=openapi.TYPE_ARRAY,
        #             items=openapi.Schema(type=openapi.TYPE_INTEGER, nullable=True),
        #             default=[38264, 38141, 38023, 38149, 38146, 38265, 38263, 38262],
        #             description="Stansiya raqamlari ro'yxati (ixtiyoriy, ko'rsatilmasa barcha stansiyalar uchun)"
        #         ),
        #         'max_concurrent': openapi.Schema(
        #             type=openapi.TYPE_INTEGER,
        #             description="Maksimal parallellik soni",
        #             default=10,
        #             nullable=True
        #         )
        #     }
        # ),
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
        # Get parameters from request
        station_numbers = request.data.get('station_numbers', [38264, 38141, 38023, 38149, 38146, 38265, 38263, 38262])
        max_concurrent = request.data.get('max_concurrent', 10)
        
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
        
        # Process each station
        stations_processed = []
        
        # Create or ensure parameter names exist
        parameter_mapping = {
            'temp': self._get_parameter_name('temp'),
            'wind_speed': self._get_parameter_name('wind-speed'),
            'wind_direction': self._get_parameter_name('wind-direction'),
            'pressure': self._get_parameter_name('pressure'),
            'humidity': self._get_parameter_name('humidity'),
            'rainfall': self._get_parameter_name('rainfall'),
            'Te': self._get_parameter_name('ef-temp'),
        }
        
        # Create event loop for async operations
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Process each station one by one (not in parallel to avoid overloading)
            for station in stations:
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
                
                # Scrape data for this station
                weather_data = loop.run_until_complete(
                    self._get_weather_data_async(
                        station_id=station.number,
                        start_date_str=start_date_str,
                        end_date_str=end_date_str,
                        max_concurrent=max_concurrent
                    )
                )
                
                # Process and save the scraped data
                parameters_added = self._process_weather_data(station, weather_data, parameter_mapping)
                
                # Add to processed stations list
                stations_processed.append({
                    'station_number': station.number,
                    'station_name': station.name,
                    'parameters_added': parameters_added,
                    'start_date': start_date_str,
                    'end_date': end_date_str
                })
                
        finally:
            # Close the event loop
            loop.close()
        
        return custom_response(
            data={
                'items': stations_processed
            },
            status_code=status.HTTP_200_OK
        )
    
    def _get_parameter_name(self, slug):
        """Get a parameter name"""
        param_name = ParameterName.objects.get(
            slug=slug,
        )
        return param_name
    
    def _process_weather_data(self, station, weather_data, parameter_mapping):
        """Process and save weather data to the database"""
        parameters_added = 0
        
        if weather_data.empty:
            return parameters_added
        
        # Process each row of weather data
        for _, row in weather_data.iterrows():
            if row['datetime'] is None:
                continue
            
            # Process each parameter type
            for scraper_key, parameter_name in parameter_mapping.items():
                if scraper_key in row and row[scraper_key] and row[scraper_key] != '':
                    try:
                        # Try to convert to float (some values might be strings or have units attached)
                        value = row[scraper_key]
                        if isinstance(value, str):
                            # Remove any non-numeric characters (except decimal point and minus)
                            value = ''.join(c for c in value if c.isdigit() or c in ['.', '-'])
                            if value:
                                value = float(value)
                            else:
                                continue
                        
                        # Create parameter record
                        Parameter.objects.get_or_create(
                            station=station,
                            parameter_name=parameter_name,
                            datetime=row['datetime'],
                            defaults={'value': value}
                        )
                        parameters_added += 1
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error processing {scraper_key} value: {row[scraper_key]} - {e}")
        
        return parameters_added
    
    async def _get_weather_data_async(self, station_id, start_date_str, end_date_str=None, max_concurrent=10):
        """Async function to get weather data as a DataFrame"""
        # Parse dates
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.now()
        
        logger.info(f"Starting scrape for station {station_id} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Generate all month segments to scrape
        month_segments = self._generate_month_segments(start_date, end_date)
        
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # Create a session for all requests
        conn = aiohttp.TCPConnector(limit=max_concurrent)
        async with aiohttp.ClientSession(connector=conn) as session:
            # Create tasks for each month segment
            tasks = [
                self._scrape_month(session, station_id, year, month, first_day, last_day, semaphore)
                for year, month, first_day, last_day in month_segments
            ]
            
            # Run tasks
            results = await asyncio.gather(*tasks)
        
        # Flatten the results
        all_data = [item for sublist in results for item in sublist]
        
        # Convert to dataframe
        df = pd.DataFrame(all_data)
        
        # Sort by datetime
        if not df.empty and 'datetime' in df.columns:
            df = df.sort_values(by='datetime')
        
        return df
    
    def _generate_month_segments(self, start_date, end_date):
        """Generate all month segments with the correct start/end days."""
        segments = []
        current_date = start_date
        
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            
            # Calculate the first day for this segment
            first_day = 1
            if current_date.year == start_date.year and current_date.month == start_date.month:
                first_day = start_date.day
            
            # Calculate the last day for this segment
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            
            month_end = (next_month - timedelta(days=1))
            
            # If this is the end month, use the end day
            if year == end_date.year and month == end_date.month:
                last_day = end_date.day
            else:
                last_day = month_end.day
            
            segments.append((year, month, first_day, last_day))
            
            # Move to the first day of the next month
            current_date = next_month
        
        return segments
    
    async def _scrape_month(self, session, station_id, year, month, first_day, last_day, semaphore):
        """Scrape weather data for a specific month with async requests."""
        # Build the URL based on the parameters
        url = (
            f"http://www.pogodaiklimat.ru/weather.php?"
            f"id={station_id}&bday={first_day}&fday={last_day}&amonth={month}&ayear={year}&bot=2"
        )
        
        month_data = []
        
        # Use semaphore to limit concurrent requests
        async with semaphore:
            try:
                # Request the page with timeout and retry logic
                retries = 3
                for attempt in range(retries):
                    try:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                html = await response.text()
                                break
                            else:
                                if attempt == retries - 1:
                                    logger.warning(f"Failed to retrieve data for {year}-{month:02d}: HTTP {response.status}")
                                    return []
                                await asyncio.sleep(2 * (attempt + 1))  # Exponential backoff
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if attempt == retries - 1:
                            logger.warning(f"Network error for {year}-{month:02d}: {str(e)}")
                            return []
                        await asyncio.sleep(2 * (attempt + 1))  # Exponential backoff
                
                # Parse the HTML
                soup = BeautifulSoup(html, "html.parser")
                
                # Parse the left column table (Time and Date)
                left_table = soup.select_one("div.archive-table-left-column table")
                if left_table is None:
                    logger.warning(f"Left table not found for {year}-{month:02d}")
                    return []
                
                left_rows = left_table.find_all("tr")
                
                left_data = []
                # Skip the header row
                for row in left_rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        time_str = cells[0].get_text(strip=True)
                        date_str = cells[1].get_text(strip=True)
                        left_data.append({"time": time_str, "date": date_str})
                
                # Parse the right table (Weather details)
                right_table = soup.select_one("div.archive-table-wrap table")
                if right_table is None:
                    logger.warning(f"Right table not found for {year}-{month:02d}")
                    return []
                
                right_rows = right_table.find_all("tr")
                
                right_data = []
                for row in right_rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) < 18:
                        continue
                    
                    record = {
                        "wind_direction": cells[0].get_text(strip=True),
                        "wind_speed": cells[1].get_text(strip=True),
                        "visibility": cells[2].get_text(strip=True),
                        "phenomena": cells[3].get_text(strip=True),
                        "cloudiness": cells[4].get_text(strip=True),
                        "temp": cells[5].get_text(strip=True),
                        "dew_point": cells[6].get_text(strip=True),
                        "f": cells[7].get_text(strip=True),
                        "Te": cells[8].get_text(strip=True),
                        "Tes": cells[9].get_text(strip=True),
                        "comfort": cells[10].get_text(strip=True),
                        "pressure": cells[11].get_text(strip=True),
                        "Po": cells[12].get_text(strip=True),
                        "Tmin": cells[13].get_text(strip=True),
                        "Tmax": cells[14].get_text(strip=True),
                        "R": cells[15].get_text(strip=True),
                        "R24": cells[16].get_text(strip=True),
                        "S": cells[17].get_text(strip=True)
                    }
                    right_data.append(record)
                
                # Merge the two parts and create datetime field
                if len(left_data) == len(right_data):
                    for ld, rd in zip(left_data, right_data):
                        datetime_str = f"{ld['date']}.{year} {ld['time']}:00"
                        try:
                            dt = datetime.strptime(datetime_str, "%d.%m.%Y %H:%M")
                        except Exception:
                            dt = None
                        combined = {**ld, **rd, "month": month, "year": year, "datetime": dt}
                        month_data.append(combined)
            
            except Exception as e:
                logger.error(f"Error processing {month}/{year} (days {first_day}-{last_day}): {str(e)}")
            
            return month_data 