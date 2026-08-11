from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import update_session_auth_hash
from .serializers import (
    UserProfileSerializer, ChangePasswordSerializer,
    SavedVideoSerializer, JournalArchiveSerializer
)
from .models import UserProfile
from spiritual.models import VideoTrack
from journal.models import JournalEntry

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            return Response({"message": "Password updated successfully"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SavedSpiritualView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Assuming you have a ManyToManyField or separate model for saved videos
        # For now: placeholder - return all or latest
        videos = VideoTrack.objects.all()[:10]  # Replace with actual saved relation
        serializer = SavedVideoSerializer(videos, many=True)
        return Response(serializer.data)

class JournalArchiveView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        entries = JournalEntry.objects.filter(user=request.user).order_by('-created_at')
        serializer = JournalArchiveSerializer(entries, many=True)
        return Response(serializer.data)

class HelpCenterView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "customer_service": "support@soulciety.com",
            "whatsapp": "https://wa.me/1234567890",
            "faq": ["How to reset password?", "Contact support", "..."]
        }
        return Response(data)