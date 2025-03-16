from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import CSRFCheck
from rest_framework import exceptions
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.tokens import RefreshToken

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom authentication class that extends JWTAuthentication
    to handle JWT refresh tokens from cookies.
    """
    
    def authenticate(self, request):
        # Get the refresh token from the cookie
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        
        if refresh_token is None:
            return None
            
        # Verify the token and get the user
        try:
            # Directly use RefreshToken
            token = RefreshToken(refresh_token)
            
            # Get user_id from token payload
            user_id = token.payload.get('user_id')
            if not user_id:
                return None
                
            # Get user using default get_user method
            user = self.get_user(token)
            
            return (user, token)
        except Exception as e:
            # Don't raise exception for unauthenticated requests
            # Just return None to allow the view's permission classes to handle it
            return None
    
    def enforce_csrf(self, request):
        """
        Enforce CSRF validation for cookie-based authentication.
        """
        check = CSRFCheck(request)
        # PopulateMiddleware is required for CsrfViewMiddleware.
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            # CSRF failed, bail with explicit error message
            raise exceptions.PermissionDenied('CSRF Failed: %s' % reason) 