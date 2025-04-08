from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from ..utils import custom_response
from ..error_messages import VALIDATION_ERROR_MESSAGES, AUTH_ERROR_MESSAGES
from ..models import Station


class StationListView(APIView):
    """
    View for retrieving all stations
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
            401: "Autentifikatsiya muvaffaqiyatsiz",
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


class StationCreateView(APIView):
    """
    View for creating a new station
    """
    permission_classes = [permissions.IsAuthenticated]
    
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
            400: "Noto'g'ri so'rov parametrlari",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            409: "Ushbu raqamli stansiya allaqachon mavjud",
        }
    )
    def post(self, request):
        # Validate required fields
        required_fields = ['number', 'name', 'lon', 'lat']
        for field in required_fields:
            if field not in request.data:
                return custom_response(
                    detail=VALIDATION_ERROR_MESSAGES['required'].format(field=field),
                    status_code=status.HTTP_400_BAD_REQUEST,
                    success=False
                )
        
        # Check if station with this number already exists
        if Station.objects.filter(number=request.data['number']).exists():
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['station_exists'].format(number=request.data['number']),
                status_code=status.HTTP_409_CONFLICT,
                success=False
            )
        
        # Validate coordinates
        try:
            lon = float(request.data['lon'])
            lat = float(request.data['lat'])
        except (ValueError, TypeError):
            return custom_response(
                detail=VALIDATION_ERROR_MESSAGES['invalid'].format(field='Koordinatalar'),
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
        
        # Create new station
        station = Station.objects.create(
            number=request.data['number'],
            name=request.data['name'],
            height=request.data['height'],
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


class StationEditView(APIView):
    """
    View for updating an existing station
    """
    permission_classes = [permissions.IsAuthenticated]
    
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
            400: "Noto'g'ri so'rov parametrlari",
            401: "Autentifikatsiya muvaffaqiyatsiz",
            404: "Stansiya topilmadi",
        }
    )
    def put(self, request, station_number):
        # Check if station exists
        try:
            station = Station.objects.get(number=station_number)
        except Station.DoesNotExist:
            return custom_response(
                detail=AUTH_ERROR_MESSAGES['not_found'].format(item="Stansiya"),
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