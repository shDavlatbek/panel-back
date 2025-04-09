# from django.urls import reverse
# from rest_framework.test import APITestCase
# from rest_framework import status
# from web.models import GeographicArea
# import json


# class HexGridAPIViewTests(APITestCase):
#     """Test cases for the HexGridAPIView"""
    
#     def setUp(self):
#         """Set up for the tests"""
#         self.hexgrid_url = reverse('web:hex-grid')
        
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
    
#     def test_get_hexgrid_success(self):
#         """Test getting hex grid successfully"""
#         response = self.client.get(self.hexgrid_url)
        
#         # Check response status
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(response.data['success'])
        
#         # Check response data structure
#         self.assertIn('result', response.data)
        
#         # Check that the result is a GeoJSON feature collection
#         result = response.data['result']
#         self.assertEqual(result['type'], 'FeatureCollection')
#         self.assertIn('features', result)
#         self.assertIsInstance(result['features'], list)
        
#         # Check that features are included
#         features = result['features']
#         self.assertGreater(len(features), 0)
        
#         # Check the structure of the first feature
#         first_feature = features[0]
#         self.assertEqual(first_feature['type'], 'Feature')
#         self.assertIn('geometry', first_feature)
#         self.assertIn('properties', first_feature)
#         self.assertEqual(first_feature['geometry']['type'], 'Polygon')
    
#     def test_get_hexgrid_custom_bounds(self):
#         """Test getting hex grid with custom bounds"""
#         # Delete the geographic area to force using request parameters
#         self.geo_area.delete()
        
#         # Test with custom bounds
#         response = self.client.get(
#             self.hexgrid_url,
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
        
#         # Verify it's a GeoJSON feature collection
#         result = response.data['result']
#         self.assertEqual(result['type'], 'FeatureCollection')
#         self.assertIn('features', result)
    
#     def test_get_hexgrid_invalid_params(self):
#         """Test getting hex grid with invalid parameters"""
#         # Delete the geographic area to force using request parameters
#         self.geo_area.delete()
        
#         # Test with invalid parameters
#         response = self.client.get(
#             self.hexgrid_url,
#             {
#                 'north': 'invalid',
#                 'south': 41.0,
#                 'east': 70.0,
#                 'west': 69.0
#             }
#         )
        
#         # Should fail with 400 Bad Request
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
#         self.assertFalse(response.data['success']) 