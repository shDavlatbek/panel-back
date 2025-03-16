from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

User = get_user_model()

class JWTCookieMiddleware:
    """
    Middleware to process JWT authentication from cookies
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        self.process_request(request)
        response = self.get_response(request)
        return response
        
    def process_request(self, request):
        """
        Process the request to extract user from JWT token in cookie
        """
        # Skip if user is already authenticated
        if request.user and request.user.is_authenticated:
            return
            
        refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
        
        if refresh_token:
            try:
                # Directly parse the refresh token
                token = RefreshToken(refresh_token)
                
                # Get user_id from token payload
                user_id = token.payload.get('user_id')
                if not user_id:
                    return
                
                # Get user from id
                try:
                    user = User.objects.get(id=user_id)
                    if user:
                        # Set request.user
                        request.user = user
                except User.DoesNotExist:
                    pass
                
            except (InvalidToken, TokenError):
                # Token is invalid - simply continue with unauthenticated request
                pass 