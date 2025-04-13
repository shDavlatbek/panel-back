import asyncio
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# Set up logging
logger = logging.getLogger(__name__)

async def scrape_month(session, station_id, year, month, first_day, last_day, semaphore):
    """
    Scrape weather data for a specific month with async requests.
    
    Args:
        session (aiohttp.ClientSession): Session for making HTTP requests
        station_id (str): ID of the weather station
        year (int): Year to fetch data for
        month (int): Month to fetch data for
        first_day (int): First day of the month to fetch
        last_day (int): Last day of the month to fetch
        semaphore (asyncio.Semaphore): Semaphore to limit concurrent requests
        
    Returns:
        list: List of dictionaries containing weather data for each timestamp
    """
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
                logger.warning(f"Left table not found for {year}-{month:02d}, days {first_day}-{last_day}, station {station_id}")
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
                logger.warning(f"Right table not found for {year}-{month:02d}, days {first_day}-{last_day}, station {station_id}")
                return []
            
            right_rows = right_table.find_all("tr")
            
            right_data = []
            for row in right_rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 18:
                    continue
                
                # Extract all weather parameters from the table columns
                record = {
                    "wind_direction": cells[0].get_text(strip=True),  # Wind direction (e.g., С, СВ, etc.)
                    "wind_speed": cells[1].get_text(strip=True),      # Wind speed in m/s
                    "visibility": cells[2].get_text(strip=True),      # Visibility in km
                    "phenomena": cells[3].get_text(strip=True),       # Weather phenomena (rain, snow, etc.)
                    "cloudiness": cells[4].get_text(strip=True),      # Cloud coverage
                    "temp": cells[5].get_text(strip=True),            # Temperature in °C
                    "dew_point": cells[6].get_text(strip=True),       # Dew point in °C
                    "f": cells[7].get_text(strip=True),               # Relative humidity (%)
                    "Te": cells[8].get_text(strip=True),              # Effective temperature in °C
                    "Tes": cells[9].get_text(strip=True),             # Equivalent-effective temperature
                    "comfort": cells[10].get_text(strip=True),        # Comfort index
                    "pressure": cells[11].get_text(strip=True),       # Atmospheric pressure in mm Hg
                    "Po": cells[12].get_text(strip=True),             # Sea level pressure
                    "Tmin": cells[13].get_text(strip=True),           # Minimum temperature
                    "Tmax": cells[14].get_text(strip=True),           # Maximum temperature
                    "R": cells[15].get_text(strip=True),              # Precipitation in mm
                    "R24": cells[16].get_text(strip=True),            # 24-hour precipitation in mm
                    "S": cells[17].get_text(strip=True)               # Snow depth in cm
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

def generate_month_segments(start_date, end_date):
    """
    Generate all month segments with the correct start/end days.
    
    Args:
        start_date (datetime): Start date
        end_date (datetime): End date
        
    Returns:
        list: List of tuples containing (year, month, first_day, last_day)
    """
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

async def scrape_weather_data_async(station_id, start_date, end_date, max_concurrent=10, verbose=True):
    """
    Scrape weather data using async requests.
    
    Args:
        station_id (str): ID of the weather station
        start_date (datetime): Start date
        end_date (datetime): End date
        max_concurrent (int): Maximum number of concurrent requests
        verbose (bool): Whether to print progress information
        
    Returns:
        pandas.DataFrame: DataFrame containing the weather data
    """
    # Generate all month segments to scrape with proper start/end days
    month_segments = generate_month_segments(start_date, end_date)
    
    if verbose:
        logger.info(f"Preparing to scrape {len(month_segments)} month segments for station {station_id}")
        for i, (year, month, first_day, last_day) in enumerate(month_segments):
            logger.info(f"  {i+1}. {year}-{month:02d}: days {first_day}-{last_day}")
    
    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # Create a session for all requests
    conn = aiohttp.TCPConnector(limit=max_concurrent)
    async with aiohttp.ClientSession(connector=conn) as session:
        # Create tasks for each month segment
        tasks = [
            scrape_month(session, station_id, year, month, first_day, last_day, semaphore)
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
    
    if verbose and not df.empty:
        logger.info(f"Scraping complete. Retrieved {len(df)} records for station {station_id}")
    
    return df

async def get_weather_data_async(station_id, start_date_str, end_date_str=None, max_concurrent=10, verbose=True):
    """
    Async function to get weather data as a DataFrame.
    
    Parameters:
    -----------
    station_id : str
        Weather station ID to query
    start_date_str : str
        Start date in 'YYYY-MM-DD' format
    end_date_str : str, optional
        End date in 'YYYY-MM-DD' format (defaults to current date)
    max_concurrent : int, optional
        Maximum number of concurrent requests (default: 10)
    verbose : bool, optional
        Whether to print progress information (default: True)
        
    Returns:
    --------
    pandas.DataFrame
        DataFrame containing the weather data with columns:
        - datetime: Timestamp of the measurement
        - wind_direction: Direction of the wind (text like 'С', 'СВ', etc.)
        - wind_speed: Wind speed in m/s
        - temp: Temperature in °C
        - pressure: Atmospheric pressure in mm Hg
        - humidity: Relative humidity (%) (from 'f' column)
        - rainfall: Precipitation in mm (from 'R' column)
        - And other weather parameters
    """
    # Parse dates
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    else:
        end_date = datetime.now()
    
    if verbose:
        logger.info(f"Starting scrape for station {station_id} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        logger.info(f"Using max concurrency of {max_concurrent} requests")
    
    # Time the execution
    start_time = time.time()
    df = await scrape_weather_data_async(station_id, start_date, end_date, max_concurrent, verbose)
    elapsed_time = time.time() - start_time
    
    if verbose:
        if df.empty:
            logger.warning(f"No data was retrieved for station {station_id}. Check the station ID and date range.")
        else:
            logger.info(f"Scraping complete. Retrieved {len(df)} records for station {station_id}")
        logger.info(f"Total time: {elapsed_time:.2f} seconds")
    
    return df 