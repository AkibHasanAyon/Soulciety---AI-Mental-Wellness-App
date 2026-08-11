from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from accounts.models import CustomUser

class JournalEntry(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='journal_entries')
    content = models.TextField()  # main journal text
    mood = models.CharField(
        max_length=50,
        blank=True,
        help_text="User-selected mood (e.g., Peaceful, Grateful, Anxious)"
    )
    tags = models.CharField(max_length=255, blank=True)  # comma-separated or JSON later
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_private = models.BooleanField(default=True)  # for future sharing/community features

    ai_insight = models.TextField(blank=True, null=True)  # generated AI insight
    has_insight = models.BooleanField(blank=True, null=True, default=False) 
        # FIX: Add null=True and blank=True
    insight_generated_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.created_at.date()}"

    class Meta:
        ordering = ['-created_at']