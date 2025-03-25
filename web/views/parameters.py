from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import SUCCESS_MESSAGES, AUTH_ERROR_MESSAGES
from ..models import Station, ParameterType, Parameter


class ParameterTypesByStationView(APIView):
    """
    View for retrieving parameter types by station number
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Stations', 'Parameter Types'],
        operation_description="Stansiya raqami bo'yicha parametr turlarini olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Parametr turlari ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'parameter_types': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'slug': openapi.Schema(type=openapi.TYPE_STRING),
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'unit': openapi.Schema(type=openapi.TYPE_STRING)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def get(self, request, station_number):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        parameter_types = station.parameter_types
        parameter_types_data = []
        
        for parameter_type in parameter_types:
            parameter_types_data.append({
                'slug': parameter_type.slug,
                'id': parameter_type.id,
                'name': parameter_type.name,
                'unit': parameter_type.unit
            })
        
        return custom_response(
            data={
                'message': SUCCESS_MESSAGES['parameter_types_list'],
                'station': {
                    'number': station.number,
                    'name': station.name
                },
                'parameter_types': parameter_types_data
            },
            status_code=status.HTTP_200_OK
        )


class ParametersByStationView(APIView):
    """
    View for retrieving parameters by station number
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Stations', 'Parameters'],
        operation_description="Stansiya raqami bo'yicha parametrlarni olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Parametrlar ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'parameter_type_slug': openapi.Schema(type=openapi.TYPE_STRING),
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'value': openapi.Schema(type=openapi.TYPE_NUMBER)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def get(self, request, station_number):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        parameters = Parameter.objects.filter(station=station)
        parameters_data = []
        
        for parameter in parameters:
            parameters_data.append({
                'id': parameter.id,
                'parameter_type_slug': parameter.parameter_type.slug,
                'datetime': parameter.datetime,
                'value': parameter.value
            })
        
        return custom_response(
            data={
                'message': SUCCESS_MESSAGES['parameters_list'],
                'station': {
                    'number': station.number,
                    'name': station.name
                },
                'parameters': parameters_data
            },
            status_code=status.HTTP_200_OK
        )


class ParametersByTypeAndStationView(APIView):
    """
    View for retrieving parameters by parameter type and station number
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Stations', 'Parameters', 'Parameter Types'],
        operation_description="Stansiya raqami va parametr turi bo'yicha parametrlarni olish",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'parameter_type_slug',
                openapi.IN_PATH,
                description="Parametr turi slugi",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Parametrlar ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                                'station': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING)
                                    }
                                ),
                                'parameter_type_slug': openapi.Schema(type=openapi.TYPE_STRING),
                                'parameters': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'datetime': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'value': openapi.Schema(type=openapi.TYPE_NUMBER)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya yoki parametr turi topilmadi",
        }
    )
    def get(self, request, station_number, parameter_type_slug):
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        try:
            parameter_type = ParameterType.objects.get(slug=parameter_type_slug)
        except ParameterType.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Parametr turi"),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        parameters = Parameter.objects.filter(station=station, parameter_type=parameter_type)
        parameters_data = []
        
        for parameter in parameters:
            parameters_data.append({
                'id': parameter.id,
                'datetime': parameter.datetime,
                'value': parameter.value
            })
        
        return custom_response(
            data={
                'message': SUCCESS_MESSAGES['parameters_by_type_list'],
                'station': {
                    'number': station.number,
                    'name': station.name
                },
                'parameter_type_slug': parameter_type.slug,
                'parameters': parameters_data
            },
            status_code=status.HTTP_200_OK
        ) 