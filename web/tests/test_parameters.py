# from django.urls import reverse
# from django.contrib.auth.models import User
# from rest_framework.test import APITestCase
# from rest_framework import status
# from web.models import Station, Parameter, ParameterType
# from datetime import datetime, timezone, timedelta


# class ParameterViewsTests(APITestCase):
#     """Test cases for the Parameter-related views"""
    
#     def setUp(self):
#         """Set up for the tests"""
#         # Create test user
#         self.admin_user = User.objects.create_user(
#             username="adminuser",
#             password="adminpassword",
#             is_staff=True
#         )
        
#         # Create test station
#         self.station = Station.objects.create(
#             number=301,
#             name="Test Parameter Station",
#             lat=41.3,
#             lon=69.3
#         )
        
#         # Create parameter types
#         self.parameter_types = [
#             ParameterType.objects.create(
#                 name="Air Quality Index",
#                 slug="aqi",
#                 unit="AQI",
#                 decimals=0
#             ),
#             ParameterType.objects.create(
#                 name="PM2.5",
#                 slug="pm25",
#                 unit="μg/m³",
#                 decimals=1
#             ),
#             ParameterType.objects.create(
#                 name="Temperature",
#                 slug="temp",
#                 unit="°C",
#                 decimals=1
#             )
#         ]
        
#         # Create parameters
#         current_time = datetime.now(timezone.utc)
        
#         # AQI parameters
#         for i in range(5):
#             Parameter.objects.create(
#                 station=self.station,
#                 parameter_type=self.parameter_types[0],  # AQI
#                 value=50 + i * 5,  # Different values
#                 datetime=current_time - timedelta(hours=i)
#             )
        
#         # PM2.5 parameters
#         for i in range(3):
#             Parameter.objects.create(
#                 station=self.station,
#                 parameter_type=self.parameter_types[1],  # PM2.5
#                 value=15.5 + i * 2.5,
#                 datetime=current_time - timedelta(hours=i)
#             )
        
#         # Temperature parameters
#         for i in range(2):
#             Parameter.objects.create(
#                 station=self.station,
#                 parameter_type=self.parameter_types[2],  # Temperature
#                 value=25.5 - i * 1.5,
#                 datetime=current_time - timedelta(hours=i)
#             )
        
#         # URLs for the view endpoints
#         self.parameter_types_url = reverse('web:parameter_types_by_station', kwargs={'station_number': self.station.number})
#         self.parameters_by_station_url = reverse('web:parameters_by_station', kwargs={'station_number': self.station.number})
#         self.parameters_by_type_url = reverse(
#             'web:parameters_by_type_and_station',
#             kwargs={
#                 'station_number': self.station.number,
#                 'parameter_type_slug': self.parameter_types[0].slug  # AQI
#             }
#         )
    
#     def test_get_parameter_types_by_station(self):
#         """Test getting parameter types for a station"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # Make the request
#         response = self.client.get(self.parameter_types_url)
        
#         # Check response
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check that we get all parameter types
#         result = response.data['result']
#         self.assertEqual(len(result), 3)
        
#         # Check the structure of the first parameter type
#         first_param_type = result[0]
#         self.assertIn('id', first_param_type)
#         self.assertIn('name', first_param_type)
#         self.assertIn('slug', first_param_type)
#         self.assertIn('unit', first_param_type)
        
#         # All parameter type slugs should be present
#         slugs = [pt['slug'] for pt in result]
#         for pt in self.parameter_types:
#             self.assertIn(pt.slug, slugs)
    
#     def test_get_parameters_by_station(self):
#         """Test getting parameters for a station"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # Make the request
#         response = self.client.get(self.parameters_by_station_url)
        
#         # Check response
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check that we get parameters
#         result = response.data['result']
#         # Should return the 10 parameters we created (5 AQI + 3 PM2.5 + 2 Temperature)
#         self.assertEqual(len(result), 10)
        
#         # Check structure of the first parameter
#         first_param = result[0]
#         self.assertIn('id', first_param)
#         self.assertIn('parameter_type', first_param)
#         self.assertIn('value', first_param)
#         self.assertIn('datetime', first_param)
    
#     def test_get_parameters_by_type_and_station(self):
#         """Test getting parameters by type for a station"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # Make the request for AQI parameters
#         response = self.client.get(self.parameters_by_type_url)
        
#         # Check response
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check that we get only AQI parameters
#         result = response.data['result']
#         self.assertEqual(len(result), 5)  # Should be 5 AQI parameters
        
#         # Verify all are of AQI type
#         for param in result:
#             self.assertEqual(param['parameter_type']['slug'], 'aqi')
    
#     def test_get_parameters_with_limit(self):
#         """Test getting parameters with a limit"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # Make the request with limit=2
#         response = self.client.get(f"{self.parameters_by_station_url}?limit=2")
        
#         # Check response
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check that we get only 2 parameters
#         result = response.data['result']
#         self.assertEqual(len(result), 2)
    
#     def test_get_parameters_station_not_found(self):
#         """Test getting parameters for a non-existent station"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # URL with non-existent station ID
#         non_existent_url = reverse('web:parameters_by_station', kwargs={'station_number': 9999})
        
#         # Make the request
#         response = self.client.get(non_existent_url)
        
#         # Should fail with 404 Not Found
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertFalse(response.data['success'])
    
#     def test_get_parameters_by_invalid_type(self):
#         """Test getting parameters for an invalid parameter type"""
#         # Authenticate
#         self.client.force_authenticate(user=self.admin_user)
        
#         # URL with invalid parameter type
#         invalid_type_url = reverse(
#             'web:parameters_by_type_and_station',
#             kwargs={
#                 'station_number': self.station.number,
#                 'parameter_type_slug': 'invalid-type'
#             }
#         )
        
#         # Make the request
#         response = self.client.get(invalid_type_url)
        
#         # Should fail with 404 Not Found
#         self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
#         self.assertFalse(response.data['success']) 