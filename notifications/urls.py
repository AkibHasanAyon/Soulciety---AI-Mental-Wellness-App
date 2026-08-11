from django.urls import path
from .views import (
    DeviceTokenView,
    NotificationListView,
    NotificationMarkReadView,
    NotificationSettingsView,
    NotificationActionView,
)

urlpatterns = [
    # Device token management (for push notifications)
    path('device-token/', DeviceTokenView.as_view(), name='device-token'),

    # List notifications
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),

    # Mark single notification as read
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notification-read'),
    
        # NEW: Action/Redirect route
    path('notifications/<int:pk>/action/', NotificationActionView.as_view(), name='notification-action'),

    # Mark all notifications as read
    path('notifications/read-all/', NotificationMarkReadView.as_view(), name='notifications-read-all'),

    # Notification settings (toggle push)
    path('settings/', NotificationSettingsView.as_view(), name='notification-settings'),
]   
