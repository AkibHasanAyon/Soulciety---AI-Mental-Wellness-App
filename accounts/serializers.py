from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from .utils import generate_otp, send_otp_email
from .models import OTP
from accounts.models import CustomUser
from user_profiles.models import UserProfile
from typing import cast

User = get_user_model()

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)  # Minimum 8 chars
    confirm_password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        """
        Custom password validation:
        - At least 8 characters (already enforced by min_length)
        - Use Django's built-in validators for strength
        """
        try:
            validate_password(value)  # Django's default validators
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        # Check password match
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")

        # Check if email already exists
        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError("Email already registered.")

        return data

    # accounts/serializers.py
    def save(self):
        if not hasattr(self, "validated_data"):
            raise serializers.ValidationError("Data must be validated before saving.")

        validated_data = cast(dict, self.validated_data)

        full_name = validated_data.get('full_name', '').strip()
        email = validated_data['email']

        # Create user — only email needed (first_name/last_name left blank)
        user = User(
            email=email,
            is_active=False  # Wait for OTP verification
        )
        user.set_password(validated_data['password'])
        user.save()

        # Create profile and save full_name
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.full_name = full_name
        profile.save()

        # Generate and send OTP
        otp_code = generate_otp()
        OTP.objects.create(user=user, otp_code=otp_code)
        send_otp_email(user.email, otp_code)

        return user
    
    


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.check_password(data['password']):
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account not verified. Please verify via OTP.")
        data['user'] = user
        return data


class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, data):
        user = CustomUser.objects.filter(email=data['email']).first()  # ← Now this works
        # OR better: user = User.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")
        
        otp_obj = OTP.objects.filter(user=user, otp_code=data['otp'], is_used=False).last()
        if not otp_obj:
            raise serializers.ValidationError("Invalid or expired OTP.")
        
        from .utils import is_otp_valid
        if not is_otp_valid(otp_obj):
            raise serializers.ValidationError("OTP has expired.")
        
        otp_obj.is_used = True
        otp_obj.save()
        
        user.is_active = True
        user.save()
        
        data['user'] = user
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user with this email.")
        return value


class ResetPasswordWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")

        user = CustomUser.objects.filter(email=data['email']).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        otp_obj = OTP.objects.filter(user=user, otp_code=data['otp'], is_used=False).last()
        if not otp_obj:
            raise serializers.ValidationError("Invalid or expired OTP.")

        if otp_obj.created_at + timezone.timedelta(minutes=10) < timezone.now():
            raise serializers.ValidationError("OTP has expired.")

        data['user'] = user
        data['otp_obj'] = otp_obj
        return data


class SocialAuthSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=255)
    image = serializers.URLField(required=False, allow_blank=True, allow_null=True)