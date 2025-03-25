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
    path('parameter-types/<str:station_number>/', ParameterTypesByStationView.as_view(), name='parameter_types_by_station'),
    path('parameters/<str:station_number>/', ParametersByStationView.as_view(), name='parameters_by_station'),
    path('parameters/<str:station_number>/<slug:parameter_type_slug>/', 
         ParametersByTypeAndStationView.as_view(), name='parameters_by_type_and_station'),
] 