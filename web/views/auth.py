from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import LOGIN_ERROR_MESSAGES, AUTH_ERROR_MESSAGES


def get_token_for_user(user):
    """
    Get or create a single token for user
    """
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


class LoginView(APIView):
    """
    View for user login - returns a single token in response
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        tags=['Authorization'],
        operation_description="Foydalanuvchi kirish endpointi",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['username', 'password'],
            properties={
                'username': openapi.Schema(type=openapi.TYPE_STRING),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_PASSWORD),
            },
        ),
        responses={
            200: openapi.Response(
                description="Kirish muvaffaqiyatli",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                                'is_admin': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                                'permissions': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING)),
                                'token': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: f"Bad Request: {LOGIN_ERROR_MESSAGES['missing_fields']}",
            401: f"Unauthorized: {LOGIN_ERROR_MESSAGES['invalid_credentials']}"
        }
    )
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if username is None or password is None:
            return custom_response(
                detail=LOGIN_ERROR_MESSAGES['missing_fields'],
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
            
        user = authenticate(username=username, password=password)
        
        if user is None:
            return custom_response(
                detail=LOGIN_ERROR_MESSAGES['invalid_credentials'],
                status_code=status.HTTP_401_UNAUTHORIZED,
                success=False
            )
        
        # Generate token
        token = get_token_for_user(user)
        
        user_data = {
            'username': user.username,
            'is_admin': user.is_staff,
            'permissions': [permission for permission in user.get_all_permissions()]
        }
        
        # Prepare response with token in the body
        response = custom_response(
            data={
                **user_data,
                'token': token
            },
            status_code=status.HTTP_200_OK
        )
        
        return response