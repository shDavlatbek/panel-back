from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase
from rest_framework import status
from web.models import Station
import json


class StationViewTests(APITestCase):
    """Test cases for the StationView"""
    
    def setUp(self):
        """Set up for the tests"""
        # Create test users
        self.admin_user = User.objects.create_user(
            username="adminuser",
            password="adminpassword",
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser",
            password="regularpassword",
            is_staff=False
        )
        
        # Add permissions to the regular user
        content_type = ContentType.objects.get_for_model(Station)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_station'
        )
        self.regular_user.user_permissions.add(view_permission)
        
        # Create test stations
        self.stations = [
            Station.objects.create(
                number=100 + i,  # Adding unique number for each station
                name=f"Test Station {i}",
                lat=41.0 + (i * 0.1),
                lon=69.0 + (i * 0.1),
                height=100 + (i * 10)
            ) for i in range(1, 4)
        ]
        
        self.stations_url = reverse('web:stations_list')
    
    def test_list_stations_authenticated(self):
        """Test listing stations when authenticated"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Make the request
        response = self.client.get(self.stations_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('result', response.data)
        self.assertEqual(len(response.data['result']), 3)
        
        # Verify structure of first station in response
        first_station = response.data['result'][0]
        self.assertIn('number', first_station)
        self.assertIn('name', first_station)
        self.assertIn('lat', first_station)
        self.assertIn('lon', first_station)
        self.assertIn('height', first_station)
    
    def test_list_stations_with_permission(self):
        """Test listing stations with view permission"""
        # Authenticate as regular user with permission
        self.client.force_authenticate(user=self.regular_user)
        
        # Make the request
        response = self.client.get(self.stations_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
    
    def test_list_stations_unauthenticated(self):
        """Test listing stations when not authenticated"""
        # Don't authenticate
        response = self.client.get(self.stations_url)
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_create_station_as_admin(self):
        """Test creating a station as admin"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Data for new station
        new_station_data = {
            "number": 999,  # Required unique station number
            "name": "New Test Station",
            "lat": 41.5,
            "lon": 69.5,
            "height": 150
        }
        
        # Make the request
        response = self.client.post(
            self.stations_url,
            new_station_data,
            format='json'
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify data in response
        result = response.data['result']
        self.assertEqual(result['number'], new_station_data['number'])
        self.assertEqual(result['name'], new_station_data['name'])
        self.assertEqual(result['lat'], new_station_data['lat'])
        self.assertEqual(result['lon'], new_station_data['lon'])
        self.assertEqual(result['height'], new_station_data['height'])
        
        # Verify station was created in database
        self.assertTrue(Station.objects.filter(number=999).exists())
    
    def test_create_station_without_permission(self):
        """Test creating a station without permission"""
        # Authenticate as regular user
        self.client.force_authenticate(user=self.regular_user)
        
        # Data for new station
        new_station_data = {
            "number": 1000,
            "name": "Unauthorized Station",
            "lat": 41.6,
            "lon": 69.6,
            "height": 160
        }
        
        # Make the request
        response = self.client.post(
            self.stations_url,
            new_station_data,
            format='json'
        )
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success'])


class StationDetailViewTests(APITestCase):
    """Test cases for the StationDetailView"""
    
    def setUp(self):
        """Set up for the tests"""
        # Create test users
        self.admin_user = User.objects.create_user(
            username="adminuser",
            password="adminpassword",
            is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="regularuser",
            password="regularpassword",
            is_staff=False
        )
        
        # Add permissions to the regular user
        content_type = ContentType.objects.get_for_model(Station)
        view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_station'
        )
        self.regular_user.user_permissions.add(view_permission)
        
        # Create test station
        self.station = Station.objects.create(
            number=500,
            name="Test Station Detail",
            lat=41.5,
            lon=69.5,
            height=150
        )
        
        self.station_detail_url = reverse('web:stations_detail', kwargs={'station_number': self.station.number})
    
    def test_get_station_detail(self):
        """Test getting station details"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Make the request
        response = self.client.get(self.station_detail_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify data in response
        result = response.data['result']
        self.assertEqual(result['number'], self.station.number)
        self.assertEqual(result['name'], self.station.name)
        self.assertEqual(result['lat'], self.station.lat)
        self.assertEqual(result['lon'], self.station.lon)
        self.assertEqual(result['height'], self.station.height)
    
    def test_update_station_as_admin(self):
        """Test updating a station as admin"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Data for update
        update_data = {
            "name": "Updated Station Name",
            "height": 175
        }
        
        # Make the request
        response = self.client.patch(
            self.station_detail_url,
            update_data,
            format='json'
        )
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify data in response
        result = response.data['result']
        self.assertEqual(result['name'], update_data['name'])
        self.assertEqual(result['height'], update_data['height'])
        
        # Refresh from database and verify
        self.station.refresh_from_db()
        self.assertEqual(self.station.name, update_data['name'])
        self.assertEqual(self.station.height, update_data['height'])
    
    def test_delete_station_as_admin(self):
        """Test deleting a station as admin"""
        # Authenticate as admin
        self.client.force_authenticate(user=self.admin_user)
        
        # Make the request
        response = self.client.delete(self.station_detail_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Verify station was deleted
        self.assertFalse(Station.objects.filter(number=self.station.number).exists())
    
    def test_update_station_without_permission(self):
        """Test updating a station without permission"""
        # Authenticate as regular user
        self.client.force_authenticate(user=self.regular_user)
        
        # Data for update
        update_data = {
            "name": "Unauthorized Update",
        }
        
        # Make the request
        response = self.client.patch(
            self.station_detail_url,
            update_data,
            format='json'
        )
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data['success']) 