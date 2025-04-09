# from django.urls import reverse
# from django.test import TestCase, Client


# class MapViewTests(TestCase):
#     """Test cases for the MapView"""
    
#     def setUp(self):
#         """Set up for the tests"""
#         self.client = Client()
#         self.map_url = reverse('web:map-view')
    
#     def test_map_view_loads(self):
#         """Test that the map view loads correctly"""
#         response = self.client.get(self.map_url)
        
#         # Check that the response is 200 OK
#         self.assertEqual(response.status_code, 200)
        
#         # Check that the response is HTML
#         self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        
#         # Check that the template is used
#         self.assertTemplateUsed(response, 'map.html')
    
#     def test_map_view_accessible_without_auth(self):
#         """Test that the map view is accessible without authentication"""
#         # No authentication needed
#         response = self.client.get(self.map_url)
        
#         # Should be accessible
#         self.assertEqual(response.status_code, 200) 