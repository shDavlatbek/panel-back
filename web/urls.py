from django.urls import path
from .views import (
    LoginView, UserMeView, 
    StationView, StationDetailView, ParameterNameView, 
    ParametersView,
    HexGridAPIView, HexagonDataAPIView, MapView,
    ParameterScrapeView, StationParametersView,
    ParameterChartView, ParameterAvgChartView, ParameterAllChartView
)
from .views.stats import StatisticsView, MonthlyStatsView, CorrelationView

app_name = 'web'

urlpatterns = [
    path('auth/login', LoginView.as_view(), name='login'),
    path('users/me', UserMeView.as_view(), name='user_me'),
    
    # Station endpoints
    path('stations', StationView.as_view(), name='stations_list'),
    path('stations/<str:station_number>', StationDetailView.as_view(), name='stations_detail'),
    path('parameter-names', ParameterNameView.as_view(), name='parameter_names'),
    
    # Parameters endpoints - specific routes first, then generic patterns
    path('parameters/scrape', ParameterScrapeView.as_view(), name='parameters_scrape'),
    path('parameters', ParametersView.as_view(), name='parameters_all'),
    path('parameters/<str:station_number>', StationParametersView.as_view(), name='parameters_by_station'),
    
    # Chart endpoints
    path('charts/avg', ParameterAvgChartView.as_view(), name='parameter_charts_avg'),
    path('charts/all', ParameterAllChartView.as_view(), name='parameter_charts_all'),
    path('charts/<str:station_number>', ParameterChartView.as_view(), name='parameter_charts'),
         
    # # Hex grid and data endpoints
    path('hexgrid', HexGridAPIView.as_view(), name='hex-grid'),
    path('hexdata', HexagonDataAPIView.as_view(), name='hex-data'),
    
    # Map view
    path('map/', MapView.as_view(), name='map-view'),
    
    # Statistics endpoints
    path('stats', StatisticsView.as_view(), name='stats'),
    path('stats/monthly', MonthlyStatsView.as_view(), name='monthly_stats'),
    path('stats/correlation', CorrelationView.as_view(), name='correlation'),
] 