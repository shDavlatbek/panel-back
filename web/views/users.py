from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response


class UserMeView(APIView):
    """
    View for retrieving authenticated user's profile information
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Users'],
        operation_description="Foydalanuvchi profili ma'lumotlarini olish endpointi",
        responses={
            200: openapi.Response(
                description="Foydalanuvchi ma'lumotlari muvaffaqiyatli olindi",
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
        user = request.user
        user_data = {
            'username': user.username,
            'is_admin': user.is_admin,
            'permissions': [permission.codename for permission in user.get_all_permissions()]
        }
        
        return custom_response(
            data={
                **user_data
            },
            status_code=status.HTTP_200_OK
        ) 