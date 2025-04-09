# from django.urls import reverse
# from rest_framework.test import APITestCase
# from rest_framework import status
# from web.models import GeographicArea, Station, Parameter, ParameterType
# import json
# from datetime import datetime, timezone


# class HexagonDataAPIViewTests(APITestCase):
#     """Test cases for the HexagonDataAPIView"""
    
#     def setUp(self):
#         """Set up for the tests"""
#         self.hexdata_url = reverse('web:hex-data')
        
#         # Create a test geographic area
#         self.geo_area = GeographicArea.objects.create(
#             name="Test Area",
#             north=41.5,
#             south=41.0,
#             east=69.5,
#             west=69.0,
#             preferred_resolution=6,
#             coordinates=json.dumps([
#                 [69.0, 41.0],
#                 [69.5, 41.0],
#                 [69.5, 41.5],
#                 [69.0, 41.5],
#                 [69.0, 41.0]
#             ])
#         )
        
#         # Create parameter types
#         self.aqi_type = ParameterType.objects.create(
#             name="Air Quality Index",
#             slug="aqi",
#             unit="AQI",
#             decimals=0
#         )
        
#         self.pm25_type = ParameterType.objects.create(
#             name="PM2.5",
#             slug="pm25",
#             unit="μg/m³",
#             decimals=1
#         )
        
#         # Create test stations with parameters
#         self.stations = []
#         station_data = [
#             {"number": 201, "name": "Station 1", "lat": 41.2, "lon": 69.2},
#             {"number": 202, "name": "Station 2", "lat": 41.3, "lon": 69.3},
#             {"number": 203, "name": "Station 3", "lat": 41.1, "lon": 69.1},
#         ]
        
#         for i, data in enumerate(station_data):
#             station = Station.objects.create(
#                 number=data["number"],
#                 name=data["name"],
#                 lat=data["lat"],
#                 lon=data["lon"]
#             )
#             self.stations.append(station)
            
#             # Add AQI parameter
#             Parameter.objects.create(
#                 station=station,
#                 parameter_type=self.aqi_type,
#                 value=50 + (i * 10),  # Different value for each station
#                 datetime=datetime.now(timezone.utc)
#             )
            
#             # Add PM2.5 parameter
#             Parameter.objects.create(
#                 station=station,
#                 parameter_type=self.pm25_type,
#                 value=15.5 + (i * 5.2),  # Different value for each station
#                 datetime=datetime.now(timezone.utc)
#             )
    
#     def test_get_hexdata_default_parameter_type(self):
#         """Test getting hex data with default parameter type (aqi)"""
#         response = self.client.get(self.hexdata_url)
        
#         # Check response status
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check response data structure
#         self.assertIn('result', response.data)
#         self.assertIsInstance(response.data['result'], list)
        
#         # Check structure of first item
#         if response.data['result']:
#             first_item = response.data['result'][0]
#             self.assertIn('hex_id', first_item)
#             self.assertIn('lat', first_item)
#             self.assertIn('lng', first_item)
#             self.assertIn('value', first_item)
    
#     def test_get_hexdata_specific_parameter_type(self):
#         """Test getting hex data with specific parameter type"""
#         # Test with PM2.5 parameter type
#         response = self.client.get(
#             self.hexdata_url,
#             {'parameter_type': 'pm25'}
#         )
        
#         # Check response status
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check response data structure
#         self.assertIn('result', response.data)
#         self.assertIsInstance(response.data['result'], list)
    
#     def test_get_hexdata_invalid_parameter_type(self):
#         """Test getting hex data with invalid parameter type"""
#         response = self.client.get(
#             self.hexdata_url,
#             {'parameter_type': 'nonexistent'}
#         )
        
#         # Should fail with 404 Not Found
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertFalse(response.data['success'])
    
#     def test_get_hexdata_custom_bounds(self):
#         """Test getting hex data with custom bounds"""
#         # Delete the geographic area to force using request parameters
#         self.geo_area.delete()
        
#         # Test with custom bounds
#         response = self.client.get(
#             self.hexdata_url,
#             {
#                 'north': 42.0,
#                 'south': 41.0,
#                 'east': 70.0,
#                 'west': 69.0,
#                 'resolution': 5
#             }
#         )
        
#         # Check response
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
#         self.assertIn('result', response.data) 