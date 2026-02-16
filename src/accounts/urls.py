from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path('register/', views.RegisterAPIView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', TokenBlacklistView.as_view(), name='logout'),
    path('password-reset/', views.PasswordResetRequestAPIView.as_view(), name='password_reset_request'),
    path('password-reset/confirm/', views.PasswordResetConfirmAPIView.as_view(), name='password_reset_confirm'),
]
