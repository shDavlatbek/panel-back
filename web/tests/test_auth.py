from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class LoginViewTests(APITestCase):
    """Test cases for the LoginView"""
    
    def setUp(self):
        """Create a test user"""
        self.username = "testuser"
        self.password = "testpassword"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
            is_staff=False
        )
        self.admin_username = "adminuser"
        self.admin_password = "adminpassword"
        self.admin_user = User.objects.create_user(
            username=self.admin_username,
            password=self.admin_password,
            is_staff=True
        )
        self.login_url = reverse('web:login')
    
    def test_login_success(self):
        """Test successful login"""
        data = {
            'username': self.username,
            'password': self.password
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['status'], 200)
        self.assertEqual(response.data['result']['username'], self.username)
        self.assertFalse(response.data['result']['is_admin'])
        self.assertIn('token', response.data['result'])
        self.assertIsNotNone(response.data['result']['token'])
        
    def test_login_success_admin(self):
        """Test successful login for admin user"""
        data = {
            'username': self.admin_username,
            'password': self.admin_password
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['result']['username'], self.admin_username)
        self.assertTrue(response.data['result']['is_admin'])
        self.assertIn('token', response.data['result'])
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': self.username,
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
    
    def test_login_missing_fields(self):
        """Test login with missing fields"""
        # Missing password
        data = {'username': self.username}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        
        # Missing username
        data = {'password': self.password}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        
        # Empty request
        data = {}
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success']) 