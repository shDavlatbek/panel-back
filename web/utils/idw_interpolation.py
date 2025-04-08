import numpy as np
from scipy.spatial import distance
import h3
from shapely.geometry import Polygon, Point
import geojson
import json
from web.utils.logger import logger

"""
IMPORTANT NOTE ABOUT COORDINATE SYSTEMS:
- H3 library functions (like h3_to_geo, geo_to_h3) use [lat, lng] order
- GeoJSON standard uses [lng, lat] order
- Leaflet library on frontend uses [lat, lng] order
- In the database, we store coordinates as [lng, lat] for GeographicArea polygons

Be careful when converting between these formats!
"""

class IDWInterpolator:
    """
    Inverse Distance Weighting (IDW) interpolation implementation using NumPy.
    """
    
    def __init__(self, points, power=3, smoothing=0.3, radius=15000000):
        """
        Initialize the IDW interpolator with points and parameters.
        
        Args:
            points: List of dictionaries with lat, lng, and aqi properties
            power: Power parameter for IDW (increased to 3 for stronger influence of closer points)
            smoothing: Smoothing factor (reduced to 0.3 for more pronounced gradients)
            radius: Search radius in meters (increased for wider station influence)
        """
        self.points = np.array([(p['lat'], p['lng']) for p in points])
        self.values = np.array([p['aqi'] for p in points])
        self.power = power
        self.smoothing = smoothing
        self.radius = radius
        
    def _haversine_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate haversine distance between two coordinates in meters.
        """
        R = 6371000  # Earth radius in meters
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(np.radians, [lat1, lng1, lat2, lng2])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlng/2)**2
        c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
        
        return R * c
    
    def interpolate(self, lat, lng):
        """
        Interpolate the value at the given coordinates.
        
        Args:
            lat: Latitude of the point
            lng: Longitude of the point
            
        Returns:
            Interpolated value
        """
        # Calculate distances to all points
        distances = np.array([self._haversine_distance(lat, lng, p[0], p[1]) for p in self.points])
        
        # If target point is the same as a known point
        if np.any(distances < 1e-10):
            return self.values[np.argmin(distances)]
        
        # Filter points within radius
        mask = distances <= self.radius
        if not np.any(mask):
            return 0
            
        # Apply IDW formula with smoothing factor
        filtered_distances = distances[mask]
        filtered_values = self.values[mask]
        
        weights = 1.0 / np.power(filtered_distances + self.smoothing, self.power)
        normalized_weights = weights / np.sum(weights)
        
        return np.sum(normalized_weights * filtered_values)

def generate_hexgrid(bounds, resolution=4, optimized=True, polygon_coords=None):
    """
    Generate a hexagonal grid using H3 within specific bounds or a custom polygon.
    
    Args:
        bounds: Dictionary with south, north, west, east coordinates
        resolution: H3 resolution (0-15, lower is larger hexagons) - default reduced to 4 for larger hexagons
        optimized: If True, use polyfill to generate hexagons (more efficient)
        polygon_coords: Optional list of [lng, lat] coordinates defining a polygon
        
    Returns:
        Dictionary with hexagons as GeoJSON features and their IDs
    """
    
    # Create the polygon for filtering
    if polygon_coords and len(polygon_coords) > 2:
        # Use custom polygon coordinates if provided
        if isinstance(polygon_coords, str):
            try:
                polygon_coords = json.loads(polygon_coords)
            except json.JSONDecodeError:
                logger.error("Failed to parse polygon coordinates JSON")
                polygon_coords = None
                
        if polygon_coords:
            # Make sure the polygon is closed
            polygon_coords = [[lng, lat] for lat, lng in polygon_coords]
            
            if polygon_coords[0] != polygon_coords[-1]:
                polygon_coords.append(polygon_coords[0])
            # Create shapely polygon for containment checks - polygon_coords is already in [lng, lat] format
            bbox = Polygon(polygon_coords)
            
            # Create a proper GeoJSON polygon for h3.polyfill
            # H3.polyfill expects GeoJSON format with coordinates in [lng, lat] order
            h3_geojson = {
                'type': 'Polygon',
                'coordinates': [polygon_coords]  # Already in correct format from database
            }
    else:
        # Create a bounding box polygon
        bbox_coords = [
            (bounds['west'], bounds['south']),
            (bounds['east'], bounds['south']),
            (bounds['east'], bounds['north']), 
            (bounds['west'], bounds['north']),
            (bounds['west'], bounds['south'])
        ]
        
        bbox = Polygon(bbox_coords)
        
        # Create a proper GeoJSON polygon for h3.polyfill
        h3_geojson = {
            'type': 'Polygon',
            'coordinates': [[
                # H3 expects [lng, lat] order in the coordinates
                [bounds['west'], bounds['south']],
                [bounds['east'], bounds['south']],
                [bounds['east'], bounds['north']],
                [bounds['west'], bounds['north']],
                [bounds['west'], bounds['south']]  # Close the polygon
            ]]
        }
    
    # Get hexagons within the bounding box or polygon
    filtered_hexagons = []
    
    try:
        if optimized:
            # Use polyfill to efficiently get hexagons that cover the polygon
            hexagons_set = h3.polyfill(h3_geojson, resolution)
            filtered_hexagons = list(hexagons_set)  # Convert set to list for further processing
            
            # If no hexagons were generated, fall back to the less optimized approach
            if not filtered_hexagons:
                logger.warning("No hexagons generated with polyfill, falling back to k_ring method")
                optimized = False
                
        if not optimized:
            # Less efficient approach using center point and expanding outward
            if polygon_coords and len(polygon_coords) > 2:
                # Use the centroid of the polygon
                polygon = Polygon(polygon_coords)
                centroid = polygon.centroid
                center_lat, center_lng = centroid.y, centroid.x
            else:
                # Use the center of the bounding box
                center_lat = (bounds['north'] + bounds['south']) / 2
                center_lng = (bounds['east'] + bounds['west']) / 2
            
            # Get the center hex and expand outward
            center_hex = h3.geo_to_h3(center_lat, center_lng, resolution)
            # Use a larger ring size to ensure coverage
            ring_size = max(5, calculate_ring_size(bounds, resolution))
            hexagons_set = h3.k_ring(center_hex, ring_size)
            
            # Filter hexagons to those within the polygon or bounding box
            filtered_hexagons = []  # Explicitly create a new list
            for hex_id in hexagons_set:
                # Get the center of the hexagon
                hex_center = h3.h3_to_geo(hex_id)  # Returns [lat, lng]
                
                # h3_to_geo returns [lat, lng] but shapely expects [lng, lat]
                # Create a Point with the correct coordinate order for shapely
                hex_point = Point(hex_center[1], hex_center[0])  # Convert to [lng, lat]
                
                # Check if the center is within the polygon/bbox
                if bbox.contains(hex_point):
                    filtered_hexagons.append(hex_id)
            
    except Exception as e:
        logger.error(f"Error generating hexgrid: {e}")
        # Return empty result in case of error
        return {
            'geojson': geojson.FeatureCollection([]),
            'hex_ids': []
        }
    
    # Ensure we have at least some hexagons
    if not filtered_hexagons:
        logger.warning("No hexagons generated, using a fallback approach")
        # Add at least one hexagon at the center of the bounding box as a fallback
        if polygon_coords and len(polygon_coords) > 2:
            # Use the centroid of the polygon
            polygon = Polygon(polygon_coords)
            centroid = polygon.centroid
            center_lat, center_lng = centroid.y, centroid.x
        else:
            # Use the center of the bounding box
            center_lat = (bounds['north'] + bounds['south']) / 2
            center_lng = (bounds['east'] + bounds['west']) / 2
            
        center_hex = h3.geo_to_h3(center_lat, center_lng, resolution)
        filtered_hexagons = [center_hex]
    
    # Convert hexagons to GeoJSON
    features = []
    hex_ids = []
    
    for hex_id in filtered_hexagons:
        try:
            # Get hexagon boundary as a list of [lat, lng] pairs
            boundary = h3.h3_to_geo_boundary(hex_id)
            
            # The h3 library returns [lat, lng] pairs, but GeoJSON needs [lng, lat]
            # Convert appropriately for GeoJSON format
            coords = [[lng, lat] for lat, lng in boundary]
            
            # Make sure the polygon is closed
            if coords and (coords[0][0] != coords[-1][0] or coords[0][1] != coords[-1][1]):
                coords.append(coords[0])
            
            # Create a GeoJSON feature
            feature = geojson.Feature(
                id=hex_id,
                geometry=geojson.Polygon([coords]),
                properties={
                    'hex_id': hex_id
                }
            )
            
            features.append(feature)
            hex_ids.append(hex_id)
        except Exception as e:
            logger.error(f"Error creating GeoJSON for hex_id {hex_id}: {e}")
            continue
    
    # Create a FeatureCollection
    feature_collection = geojson.FeatureCollection(features)
    
    return {
        'geojson': feature_collection,
        'hex_ids': hex_ids
    }

def calculate_ring_size(bounds, resolution):
    """
    Calculate an appropriate ring size based on the bounds and resolution.
    
    Args:
        bounds: Dictionary with south, north, west, east coordinates
        resolution: H3 resolution
        
    Returns:
        Appropriate ring size for h3.k_ring
    """
    # Calculate the diagonal distance of the bounding box in degrees
    lat_diff = abs(bounds['north'] - bounds['south'])
    lng_diff = abs(bounds['east'] - bounds['west'])
    diagonal = (lat_diff**2 + lng_diff**2)**0.5
    
    # Approximate hexagon size at the given resolution (in degrees)
    # These are approximate values based on H3 resolution
    hex_sizes = {
        1: 12.0,
        2: 7.0,
        3: 3.5,
        4: 1.5,
        5: 0.75,
        6: 0.35,
        7: 0.15,
        8: 0.075,
        9: 0.035,
        10: 0.015,
        11: 0.0075,
        12: 0.0036,
        13: 0.0018,
        14: 0.0009,
        15: 0.00045
    }
    
    hex_size = hex_sizes.get(resolution, 0.075)  # Default to resolution 8 if not found
    
    # Calculate the number of hexagons that would fit across the diagonal
    num_hexagons = diagonal / hex_size
    
    # Calculate ring size - adding a buffer of 2 to ensure coverage
    ring_size = max(1, int(num_hexagons / 2) + 2)
    
    return min(ring_size, 30)  # Cap at 30 to prevent excessive expansion but ensure coverage

def interpolate_hexgrid(hexgrid, interpolator):
    """
    Interpolate values for each hexagon in the grid.
    
    Args:
        hexgrid: Result from generate_hexgrid
        interpolator: IDWInterpolator instance
        
    Returns:
        Dictionary mapping hex_ids to interpolated values
    """
    hex_data = {}
    
    for hex_id in hexgrid['hex_ids']:
        try:
            # Get the center of the hexagon
            lat, lng = h3.h3_to_geo(hex_id)
            
            # Interpolate the value at this point
            value = interpolator.interpolate(lat, lng)
            
            # Store the result with appropriate encoding
            rounded_value = round(value, 2)
            hex_data[hex_id] = {
                'aqi': rounded_value,
                'description': get_aqi_description(rounded_value),
                'color': get_aqi_color(rounded_value)
            }
            
        except Exception as e:
            logger.error(f"Error interpolating data for hex_id {hex_id}: {e}")
            # Provide a default value for this hexagon
            hex_data[hex_id] = {
                'aqi': 0,
                'description': 'No data',
                'color': '#cccccc'
            }
    
    return hex_data

def get_aqi_description(aqi):
    """Get the AQI description based on the AQI value."""
    if aqi <= 50:
        return 'Good'
    elif aqi <= 100:
        return 'Moderate'
    elif aqi <= 150:
        return 'Unhealthy for Sensitive Groups'
    elif aqi <= 200:
        return 'Unhealthy'
    elif aqi <= 300:
        return 'Very Unhealthy'
    else:
        return 'Hazardous'

def get_aqi_color(aqi):
    """Get the AQI color based on the AQI value."""
    if aqi <= 50:
        return '#00e400'  # Good
    elif aqi <= 100:
        return '#ffff00'  # Moderate
    elif aqi <= 150:
        return '#ff7e00'  # Unhealthy for Sensitive Groups
    elif aqi <= 200:
        return '#ff0000'  # Unhealthy
    elif aqi <= 300:
        return '#99004c'  # Very Unhealthy
    else:
        return '#7e0023'  # Hazardous 