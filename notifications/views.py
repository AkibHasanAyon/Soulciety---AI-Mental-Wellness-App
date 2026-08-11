from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from .models import Notification, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer


class DeviceTokenView(APIView):
    """Register or update FCM device token for push notifications"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token = serializer.validated_data['token']
        platform = serializer.validated_data.get('platform', 'unknown').lower()
        print(f"Registering device token for user {request.user}: {token} on {platform}")

        # Update or create token
        device_token, created = DeviceToken.objects.update_or_create(
            user=request.user,
            token=token,
            defaults={
                'platform': platform,
                'is_active': True,
                'last_updated': timezone.now()
            }
        )

        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response({
            "message": "Token registered successfully" if created else "Token updated",
            "token_id": device_token.id,
            "platform": device_token.platform,
            "is_active": device_token.is_active
        }, status=status_code)

    def delete(self, request):
        token = request.data.get('token')
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        updated = DeviceToken.objects.filter(
            user=request.user,
            token=token
        ).update(is_active=False)

        if updated:
            return Response({"message": "Token deactivated successfully"})
        return Response({"message": "Token not found or already deactivated"})


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

        # Optional filter: only unread
        unread_only = request.query_params.get('unread', 'false').lower() == 'true'
        if unread_only:
            notifications = notifications.filter(is_read=False)

        serializer = NotificationSerializer(notifications, many=True)
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()

        return Response({
            "unread_count": unread_count,
            "notifications": serializer.data
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None):
        if pk:
            # Mark single as read
            try:
                notification = Notification.objects.get(id=pk, user=request.user)
                notification.is_read = True
                notification.save(update_fields=['is_read'])
                return Response({"message": "Notification marked as read"})
            except Notification.DoesNotExist:
                return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            # Mark all as read
            updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return Response({
                "message": "All notifications marked as read",
                "marked_count": updated
            })


class NotificationSettingsView(APIView):
    """Get or update push notification preference"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = request.user.profile.notifications_enabled
        return Response({
            "push_notifications_enabled": enabled
        })

    def post(self, request):
        enabled = request.data.get('enabled', None)
        if enabled is None:
            return Response({"error": "Field 'enabled' is required (true/false)"}, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(enabled, bool):
            return Response({"error": "'enabled' must be a boolean"}, status=status.HTTP_400_BAD_REQUEST)

        profile = request.user.profile
        profile.notifications_enabled = enabled
        profile.save(update_fields=['notifications_enabled'])

        return Response({
            "message": f"Push notifications {'enabled' if enabled else 'disabled'}",
            "push_notifications_enabled": enabled
        })
    

# notifications/views.py

class NotificationActionView(APIView):
    """
    POST /api/notifications/<pk>/action/
    Marks notification as read and returns data for app navigation.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(pk=pk, user=request.user)
            
            # Mark as read
            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=['is_read'])

            # Return the data for the mobile app to handle redirection
            return Response({
                "message": "Notification marked as read",
                "notification_type": notification.notification_type,
                "data": notification.data
            }, status=status.HTTP_200_OK)

        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)







# // Register token once app starts
# import messaging from '@react-native-firebase/messaging';

# useEffect(() => {
#   async function registerToken() {
#     const token = await messaging().getToken();
#     // POST to your backend: /api/notifications/device-token/
#     await fetch(`${API_URL}/notifications/device-token/`, {
#       method: 'POST',
#       headers: { 'Authorization': `Bearer ${jwtToken}` },
#       body: JSON.stringify({ token, platform: Platform.OS }),
#     });
#   }
#   registerToken();
# }, []);