from django.urls import path
from .views import (
    LoginView, LogoutView, UserMeView, 
    StationListView, StationCreateView, StationEditView, ParameterTypesByStationView, 
    ParametersByStationView, ParametersByTypeAndStationView
)

app_name = 'web'

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('users/me/', UserMeView.as_view(), name='user_me'),
    
    # Station endpoints
    path('stations/', StationListView.as_view(), name='stations_list'),
    path('stations/<str:station_number>/parameter-types/', ParameterTypesByStationView.as_view(), name='parameter_types_by_station'),
    path('stations/<str:station_number>/parameters/', ParametersByStationView.as_view(), name='parameters_by_station'),
    path('stations/<str:station_number>/parameter-types/<slug:parameter_type_slug>/parameters/', 
         ParametersByTypeAndStationView.as_view(), name='parameters_by_type_and_station'),
] 