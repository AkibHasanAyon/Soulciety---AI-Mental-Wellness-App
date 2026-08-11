

# Create your models here.
from django.db import models
from accounts.models import CustomUser

class ChatConversation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, blank=True)  # auto-generated or user-set
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.title or 'Untitled'}"

    class Meta:
        ordering = ['-updated_at']

class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('ai', 'Soulciety AI'),
        ('system', 'System'),
    )
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=True)  # for future notifications

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."