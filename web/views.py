from django.shortcuts import render
from django.conf import settings
from django.contrib.auth import authenticate
from django.middleware import csrf
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from datetime import datetime
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .utils import custom_response
from .error_messages import LOGIN_ERROR_MESSAGES, SUCCESS_MESSAGES, AUTH_ERROR_MESSAGES

# Create your views here.

def get_tokens_for_user(user):
    """
    Get or create refresh token for user
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
    }

def set_cookie_with_token(response, key, token, expires):
    """
    Helper function to set cookies with tokens
    """
    response.set_cookie(
        key=key,
        value=token,
        expires=expires,
        secure=settings.JWT_AUTH_SECURE,
        httponly=settings.JWT_AUTH_HTTPONLY,
        samesite=settings.JWT_AUTH_SAMESITE,
    )

class LoginView(APIView):
    """
    View for user login - issues refresh token as cookie
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
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
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: "Noto'g'ri so'rov",
            401: "Noto'g'ri login yoki parol",
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
        
        # Generate tokens
        tokens = get_tokens_for_user(user)
        refresh_token = tokens['refresh']
        
        # Prepare response
        response = custom_response(
            data={'message': SUCCESS_MESSAGES['login'], 'user': user.username},
            status_code=status.HTTP_200_OK
        )
        
        # Set CSRF token in cookie
        csrf.get_token(request)
        
        # Set refresh token in cookie
        refresh_expiration = datetime.now() + settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
        set_cookie_with_token(
            response=response,
            key=settings.JWT_AUTH_REFRESH_COOKIE,
            token=refresh_token,
            expires=refresh_expiration
        )
        
        return response

class LogoutView(APIView):
    """
    View for user logout - clears the refresh token cookie
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Foydalanuvchi chiqish endpointi",
        responses={
            200: openapi.Response(
                description="Chiqish muvaffaqiyatli",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
        }
    )
    def post(self, request):
        response = custom_response(
            data={'message': SUCCESS_MESSAGES['logout']},
            status_code=status.HTTP_200_OK
        )
        response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
        return response

class TestAuthView(APIView):
    """
    Test view to verify authentication is working
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Test autentifikatsiya endpointi",
        responses={
            200: openapi.Response(
                description="Autentifikatsiya muvaffaqiyatli",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                                'username': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
        }
    )
    def get(self, request):
        return custom_response(
            data={
                'message': SUCCESS_MESSAGES['authenticated'],
                'username': request.user.username
            },
            status_code=status.HTTP_200_OK
        )
