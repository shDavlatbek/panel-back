from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import VALIDATION_ERROR_MESSAGES, AUTH_ERROR_MESSAGES, STATION_ERROR_MESSAGES
from ..models import Station


class StationView(APIView):
    """
    View for retrieving all stations and creating new stations
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Stations'],
        operation_description="Barcha stansiyalar ro'yxatini olish",
        responses={
            200: openapi.Response(
                description="Stansiyalar ro'yxati muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'items': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(
                                        type=openapi.TYPE_OBJECT,
                                        properties={
                                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                            'number': openapi.Schema(type=openapi.TYPE_STRING),
                                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                                            'height': openapi.Schema(type=openapi.TYPE_NUMBER, nullable=True),
                                            'lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                        }
                                    )
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
        }
    )
    def get(self, request):
        stations = Station.objects.all()
        stations_data = []
        
        for station in stations:
            stations_data.append({
                'id': station.id,
                'number': station.number,
                'name': station.name,
                'height': station.height,
                'lon': station.lon,
                'lat': station.lat,
                'created_at': station.created_at,
                'updated_at': station.updated_at
            })
        
        return custom_response(
            data={
                'items': stations_data
            },
            status_code=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        tags=['Stations'],
        operation_description="Yangi stansiya qo'shish",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['number', 'name', 'height', 'lon', 'lat'],
            properties={
                'number': openapi.Schema(type=openapi.TYPE_STRING, description="Stansiya raqami"),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description="Stansiya nomi"),
                'height': openapi.Schema(type=openapi.TYPE_NUMBER, description="Stansiya balandligi", nullable=True),
                'lon': openapi.Schema(type=openapi.TYPE_NUMBER, description="Longitude koordinatasi"),
                'lat': openapi.Schema(type=openapi.TYPE_NUMBER, description="Latitude koordinatasi"),
            },
        ),
        responses={
            201: openapi.Response(
                description="Stansiya muvaffaqiyatli qo'shildi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'item': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'height': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                    }
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: f"Bad Request: {STATION_ERROR_MESSAGES['missing_field']} or {STATION_ERROR_MESSAGES['invalid_coordinates']}",
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            409: f"Conflict: {STATION_ERROR_MESSAGES['already_exists']}",
            500: f"Internal Server Error: {STATION_ERROR_MESSAGES['creation_failed']}"
        }
    )
    def post(self, request):
        # Validate required fields
        required_fields = ['number', 'name', 'lon', 'lat']
        for field in required_fields:
            if field not in request.data:
                return custom_response(
                    detail=STATION_ERROR_MESSAGES['missing_field'].format(field=field),
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
        
        # Check if station with this number already exists
        if Station.objects.filter(number=request.data['number']).exists():
            return custom_response(
                detail=STATION_ERROR_MESSAGES['already_exists'].format(number=request.data['number']),
                status_code=status.HTTP_409_CONFLICT,
                success=False
            )
        
        # Validate coordinates
        try:
            lon = float(request.data['lon'])
            lat = float(request.data['lat'])
        except (ValueError, TypeError) as e:
            return custom_response(
                detail=STATION_ERROR_MESSAGES['invalid_coordinates'].format(error=str(e)),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        try:
            # Create new station
            station = Station.objects.create(
                number=request.data['number'],
                name=request.data['name'],
                height=request.data.get('height'),
                lon=lon,
                lat=lat
            )
            
            # Prepare response
            station_data = {
                'id': station.id,
                'number': station.number,
                'name': station.name,
                'height': station.height,
                'lon': station.lon,
                'lat': station.lat,
                'created_at': station.created_at,
                'updated_at': station.updated_at
            }
            
            return custom_response(
                data={
                    'item': station_data
                },
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return custom_response(
                detail=STATION_ERROR_MESSAGES['creation_failed'].format(error=str(e)),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                success=False
            )


class StationDetailView(APIView):
    """
    View for retrieving and updating an existing station
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        tags=['Stations'],
        operation_description="Stansiya ma'lumotlarini olish",
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
                description="Stansiya ma'lumotlari muvaffaqiyatli olindi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'item': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'height': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                    }
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: f"Not Found: {STATION_ERROR_MESSAGES['not_found']}"
        }
    )
    def get(self, request, station_number):
        # Check if station exists
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=STATION_ERROR_MESSAGES['not_found'].format(number=station_number),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Prepare response
        station_data = {
            'id': station.id,
            'number': station.number,
            'name': station.name,
            'height': station.height,
            'lon': station.lon,
            'lat': station.lat,
            'created_at': station.created_at,
            'updated_at': station.updated_at
        }
        
        return custom_response(
            data={
                'item': station_data
            },
            status_code=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        tags=['Stations'],
        operation_description="Mavjud stansiyani tahrirlash",
        manual_parameters=[
            openapi.Parameter(
                'station_number',
                openapi.IN_PATH,
                description="Stansiya raqami",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(type=openapi.TYPE_STRING, description="Stansiya nomi"),
                'height': openapi.Schema(type=openapi.TYPE_NUMBER, description="Stansiya balandligi", nullable=True),
                'lon': openapi.Schema(type=openapi.TYPE_NUMBER, description="Longitude koordinatasi"),
                'lat': openapi.Schema(type=openapi.TYPE_NUMBER, description="Latitude koordinatasi"),
            },
        ),
        responses={
            200: openapi.Response(
                description="Stansiya muvaffaqiyatli tahrirlandi",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'result': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'item': openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'number': openapi.Schema(type=openapi.TYPE_STRING),
                                        'name': openapi.Schema(type=openapi.TYPE_STRING),
                                        'height': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lon': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'lat': openapi.Schema(type=openapi.TYPE_NUMBER),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                        'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME)
                                    }
                                )
                            }
                        ),
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, nullable=True),
                    }
                )
            ),
            400: f"Bad Request: {VALIDATION_ERROR_MESSAGES['invalid'].format(field='Koordinatalar')}",
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: f"Not Found: {STATION_ERROR_MESSAGES['not_found']}"
        }
    )
    def put(self, request, station_number):
        # Check if station exists
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=STATION_ERROR_MESSAGES['not_found'].format(number=station_number),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Update station fields if provided
        if 'name' in request.data:
            station.name = request.data['name']
        
        if 'height' in request.data:
            station.height = request.data['height']
        
        # Validate and update coordinates if provided
        if 'lon' in request.data or 'lat' in request.data:
            try:
                if 'lon' in request.data:
                    station.lon = float(request.data['lon'])
                if 'lat' in request.data:
                    station.lat = float(request.data['lat'])
            except (ValueError, TypeError):
                return custom_response(
                    detail=VALIDATION_ERROR_MESSAGES['invalid'].format(field='Koordinatalar'),
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
        
        # Save the updated station
        station.save()
        
        # Prepare response
        station_data = {
            'id': station.id,
            'number': station.number,
            'name': station.name,
            'height': station.height,
            'lon': station.lon,
            'lat': station.lat,
            'created_at': station.created_at,
            'updated_at': station.updated_at
        }
        
        return custom_response(
            data={
                'item': station_data
            },
            status_code=status.HTTP_200_OK
        )
    
    @swagger_auto_schema(
        tags=['Stations'],
        operation_description="Stansiyani o'chirish",
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
            204: "Stansiya muvaffaqiyatli o'chirildi",
            401: f"Unauthorized: {AUTH_ERROR_MESSAGES['not_authenticated']}",
            404: f"Not Found: {STATION_ERROR_MESSAGES['not_found']}"
        }
    )
    def delete(self, request, station_number):
        # Check if station exists
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=STATION_ERROR_MESSAGES['not_found'].format(number=station_number),
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        
        # Delete the station
        station.delete()
        
        # Return success response with no content
        return custom_response(
            status_code=status.HTTP_204_NO_CONTENT
        ) 