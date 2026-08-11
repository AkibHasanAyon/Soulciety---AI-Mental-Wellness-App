from django.urls import path
from .views import (
    RegisterView, LoginView, VerifyOTPView, ForgotPasswordView,
    ResetPasswordWithOTPView, ResendOTPView, GoogleAuthView, AppleAuthView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordWithOTPView.as_view(), name='reset-password'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('social/google/', GoogleAuthView.as_view(), name='google-auth'),
    path('social/apple/', AppleAuthView.as_view(), name='apple-auth'),
    
]