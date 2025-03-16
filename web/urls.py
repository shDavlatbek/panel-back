from django.urls import path
from .views import LoginView, LogoutView, TestAuthView

app_name = 'web'

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/test/', TestAuthView.as_view(), name='test_auth'),
] 