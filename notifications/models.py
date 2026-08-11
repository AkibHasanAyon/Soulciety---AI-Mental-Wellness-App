from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('like', 'Liked your post'),
        ('comment', 'Commented on your post'),
        ('follow', 'Started following you'),
        ('new_post', 'New post from followed user'),
        ('journal_insight', 'New AI insight on your journal'),
        ('daily_quote', 'Daily quote reminder'),
        ('community_mention', 'You were mentioned'),
        ('chat_message', 'New message from Soulciety AI'),
        ('system', 'System announcement'),
        # Healing Journey notification types (Phase 7)
        ('healing_plan_ready', 'Your healing journey is ready'),
        ('healing_day_available', 'New healing day available'),
        ('healing_evening_reminder', 'Evening healing reminder'),
        ('healing_milestone', 'Healing milestone reached'),
        ('healing_complete', 'Healing journey completed'),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=100, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(default=dict, blank=True)  # extra data: post_id, comment_id, etc.

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.notification_type} - {self.title}"

class DeviceToken(models.Model):
    """
    Stores FCM (Android) or APNs (iOS) tokens for push notifications
    """
    PLATFORM_CHOICES = (
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'token')

    def __str__(self):
        return f"{self.user.email} - {self.platform} token"
    
