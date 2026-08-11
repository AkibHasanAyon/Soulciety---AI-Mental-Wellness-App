from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
import logging
from .serializers import (
    RegisterSerializer, LoginSerializer, ResetPasswordWithOTPSerializer, VerifyOTPSerializer,
    ForgotPasswordSerializer, SocialAuthSerializer
)
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.urls import reverse
from django.contrib.auth import get_user_model
from user_profiles.models import UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


def force_https_url(url):
    if not url:
        return url

    if url.startswith('//'):
        return f"https:{url}"

    if url.startswith('http://'):
        return url.replace('http://', 'https://', 1)

    return url


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Ensure user is a single object, not a list
            if isinstance(user, list):
                user = user[0]
            return Response({
                "message": "Registration successful. Check your email for OTP.",
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': f"{user.first_name} {user.last_name}".strip()
                }
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from .serializers import VerifyOTPSerializer

class VerifyOTPView(APIView):
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer invalid: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        try:
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip()
                }
            })
        except Exception as e:
            logger.exception(f"Error generating tokens for user {user.email}: {str(e)}")
            return Response(
                {"detail": "Failed to generate authentication tokens"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from .serializers import ForgotPasswordSerializer
from .utils import generate_otp, send_otp_email
from .models import OTP
from accounts.models import CustomUser
from django.utils import timezone

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        user = CustomUser.objects.get(email=email)

        # Generate OTP and save
        otp_code = generate_otp()
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            created_at=timezone.now(),
            is_used=False
        )

        # Send OTP email
        send_otp_email(email, otp_code)

        return Response({
            "message": "OTP sent to your email. Enter it to reset password."
        }, status=status.HTTP_200_OK)


class ResetPasswordWithOTPView(APIView):
    def post(self, request):
        serializer = ResetPasswordWithOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        otp_obj = serializer.validated_data['otp_obj']

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        otp_obj.is_used = True
        otp_obj.save()

        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)
    

class ResendOTPView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Generate new OTP and save
        otp_code = generate_otp()
        OTP.objects.create(
            user=user,
            otp_code=otp_code,
            created_at=timezone.now(),
            is_used=False
        )

        # Send OTP email
        send_otp_email(email, otp_code)

        return Response({
            "message": "A new OTP has been sent to your email."
        }, status=status.HTTP_200_OK)


class SocialAuthBaseView(APIView):
    provider_name = "social"

    def _upsert_profile(self, user, full_name, image_url):
        profile, _ = UserProfile.objects.get_or_create(user=user)

        if full_name:
            profile.full_name = full_name.strip()

        if image_url and not profile.social_profile_picture_url:
            profile.social_profile_picture_url = force_https_url(image_url)

        profile.save()
        return profile

    def _build_auth_response(self, user, profile):
        refresh = RefreshToken.for_user(user)
        
        # Prefer social profile picture URL over Cloudinary uploaded one
        profile_picture_url = None
        if profile.social_profile_picture_url:
            profile_picture_url = force_https_url(profile.social_profile_picture_url)
        elif profile.profile_picture:
            profile_picture_url = force_https_url(profile.profile_picture.url)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'email': user.email,
                'full_name': profile.full_name,
                'profile_picture_url': profile_picture_url,
            }
        }

    def post(self, request):
        print(request.data)
        serializer = SocialAuthSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = (serializer.validated_data['email'] or '').lower().strip()
        full_name = (serializer.validated_data.get('full_name') or '').strip()
        image_url = (serializer.validated_data.get('image') or '').strip()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )

        if created:
            user.set_unusable_password()
            user.is_active = True
            user.save(update_fields=['password', 'is_active'])
        elif not user.is_active:
            user.is_active = True
            user.save(update_fields=['is_active'])

        profile = self._upsert_profile(user, full_name, image_url)
        return Response(self._build_auth_response(user, profile), status=status.HTTP_200_OK)


class GoogleAuthView(SocialAuthBaseView):
    provider_name = "google"


class AppleAuthView(SocialAuthBaseView):
    provider_name = "apple"

    def post(self, request):
        import traceback
        
        logger.info("==================== APPLE SIGN-IN DEBUG START ====================")
        print("==================== APPLE SIGN-IN DEBUG START ====================", flush=True)
        
        # 1. Log Request details
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Request Path: {request.path}")
        print(f"Request Method: {request.method}", flush=True)
        print(f"Request Path: {request.path}", flush=True)
        
        # Log client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        logger.info(f"Client IP: {ip}")
        print(f"Client IP: {ip}", flush=True)
        
        # Log HTTP Headers
        logger.info("HTTP Headers:")
        print("HTTP Headers:", flush=True)
        for header, val in request.headers.items():
            logger.info(f"  {header}: {val}")
            print(f"  {header}: {val}", flush=True)
            
        # Log Raw request.data
        logger.info(f"Raw Request Data: {request.data}")
        print(f"Raw Request Data: {request.data}", flush=True)
        
        try:
            # 2. Perform serialization and validation
            serializer = SocialAuthSerializer(data=request.data)
            is_valid = serializer.is_valid()
            logger.info(f"Serializer is_valid: {is_valid}")
            print(f"Serializer is_valid: {is_valid}", flush=True)
            
            if not is_valid:
                logger.error(f"Serializer validation failed! Errors: {serializer.errors}")
                print(f"Serializer validation failed! Errors: {serializer.errors}", flush=True)
                logger.info("==================== APPLE SIGN-IN DEBUG END ====================")
                print("==================== APPLE SIGN-IN DEBUG END ====================", flush=True)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            # Log Validated data
            logger.info(f"Validated Data: {serializer.validated_data}")
            print(f"Validated Data: {serializer.validated_data}", flush=True)
            
            email = (serializer.validated_data['email'] or '').lower().strip()
            full_name = (serializer.validated_data.get('full_name') or '').strip()
            image_url = (serializer.validated_data.get('image') or '').strip()
            
            logger.info(f"Processed inputs - Email: '{email}', Full Name: '{full_name}', Image URL: '{image_url}'")
            print(f"Processed inputs - Email: '{email}', Full Name: '{full_name}', Image URL: '{image_url}'", flush=True)
            
            # 3. User Upsert
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'is_active': True}
            )
            logger.info(f"User retrieved/created - Email: {user.email}, ID: {user.id}, Newly Created: {created}, Is Active: {user.is_active}")
            print(f"User retrieved/created - Email: {user.email}, ID: {user.id}, Newly Created: {created}, Is Active: {user.is_active}", flush=True)
            
            if created:
                user.set_unusable_password()
                user.is_active = True
                user.save(update_fields=['password', 'is_active'])
                logger.info("New user password set to unusable and user marked active.")
                print("New user password set to unusable and user marked active.", flush=True)
            elif not user.is_active:
                user.is_active = True
                user.save(update_fields=['is_active'])
                logger.info("Existing inactive user marked active.")
                print("Existing inactive user marked active.", flush=True)
                
            # 4. Profile Upsert
            profile = self._upsert_profile(user, full_name, image_url)
            logger.info(f"UserProfile successfully upserted - ID: {profile.id}, Full Name: '{profile.full_name}', Social Pic URL: '{profile.social_profile_picture_url}'")
            print(f"UserProfile successfully upserted - ID: {profile.id}, Full Name: '{profile.full_name}', Social Pic URL: '{profile.social_profile_picture_url}'", flush=True)
            
            # 5. Build Token Response
            auth_response = self._build_auth_response(user, profile)
            logger.info(f"Authentication response successfully generated.")
            print(f"Authentication response successfully generated.", flush=True)
            
            logger.info("==================== APPLE SIGN-IN DEBUG END ====================")
            print("==================== APPLE SIGN-IN DEBUG END ====================", flush=True)
            return Response(auth_response, status=status.HTTP_200_OK)
            
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"UNHANDLED EXCEPTION in AppleAuthView: {str(e)}\n{tb}")
            print(f"UNHANDLED EXCEPTION in AppleAuthView: {str(e)}\n{tb}", flush=True)
            logger.info("==================== APPLE SIGN-IN DEBUG END ====================")
            print("==================== APPLE SIGN-IN DEBUG END ====================", flush=True)
            return Response(
                {"error": "Internal server error occurred during Apple authentication", "detail": str(e), "traceback": tb},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        