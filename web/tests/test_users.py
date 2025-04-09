from django.urls import reverse
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APITestCase
from rest_framework import status


class UserMeViewTests(APITestCase):
    """Test cases for the UserMeView"""
    
    def setUp(self):
        """Create test users with different permissions"""
        # Create a regular user
        self.username = "testuser"
        self.password = "testpassword"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            is_staff=False
        )
        
        # Create an admin user
        self.admin_username = "adminuser"
        self.admin_password = "adminpassword"
        self.admin_user = User.objects.create_user(
            username=self.admin_username,
            password=self.admin_password,
            is_staff=True
        )
        
        # Add some permissions to the regular user
        content_type = ContentType.objects.get_for_model(User)
        can_view_permission = Permission.objects.get(
            content_type=content_type,
            codename='view_user'
        )
        self.user.user_permissions.add(can_view_permission)
        
        self.user_me_url = reverse('web:user_me')
    
    def test_get_user_profile_authenticated(self):
        """Test getting user profile when authenticated"""
        # Authenticate as the regular user
        self.client.force_authenticate(user=self.user)
        
        # Make the request
        response = self.client.get(self.user_me_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['result']['username'], self.username)
        self.assertFalse(response.data['result']['is_admin'])
        
        # Check that permissions are included in the response
        self.assertIn('permissions', response.data['result'])
        self.assertIsInstance(response.data['result']['permissions'], list)
        # Should have the permission we added
        self.assertIn('auth.view_user', response.data['result']['permissions'])
    
    def test_get_admin_profile_authenticated(self):
        """Test getting admin user profile when authenticated"""
        # Authenticate as the admin user
        self.client.force_authenticate(user=self.admin_user)
        
        # Make the request
        response = self.client.get(self.user_me_url)
        
        # Check response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['result']['username'], self.admin_username)
        self.assertTrue(response.data['result']['is_admin'])
        self.assertIn('permissions', response.data['result'])
    
    def test_get_user_profile_unauthenticated(self):
        """Test getting user profile when not authenticated"""
        # Don't authenticate
        response = self.client.get(self.user_me_url)
        
        # Should be rejected
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) 