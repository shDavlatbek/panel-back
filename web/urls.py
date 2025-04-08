from django.urls import path
from .views import (
    LoginView, UserMeView, 
    StationListCreateView, StationDetailUpdateView, ParameterTypesByStationView, 
    ParametersByStationView, ParametersByTypeAndStationView,
    HexGridAPIView, HexagonDataAPIView, MapView
)

app_name = 'web'

urlpatterns = [
    path('auth/login', LoginView.as_view(), name='login'),
    path('users/me', UserMeView.as_view(), name='user_me'),
    
    # Station endpoints
    path('stations', StationListCreateView.as_view(), name='stations_list'),
    path('stations/<str:station_number>', StationDetailUpdateView.as_view(), name='stations_detail'),
    # path('parameter-types/<str:station_number>', ParameterTypesByStationView.as_view(), name='parameter_types_by_station'),
    # path('parameters/<str:station_number>', ParametersByStationView.as_view(), name='parameters_by_station'),
    # path('parameters/<str:station_number>/<slug:parameter_type_slug>', 
    #      ParametersByTypeAndStationView.as_view(), name='parameters_by_type_and_station'),
         
    # # Hex grid and data endpoints
    # path('hexgrid', HexGridAPIView.as_view(), name='hex-grid'),
    # path('hexdata', HexagonDataAPIView.as_view(), name='hex-data'),
    
    # Map view
    path('map/', MapView.as_view(), name='map-view'),
] 