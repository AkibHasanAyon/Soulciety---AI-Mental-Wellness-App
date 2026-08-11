from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
from notifications.helpers import create_notification
from django.db.models.signals import post_save  # Needed for the signal
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)   


class Quote(models.Model):
    text = models.TextField()
    author = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.text[:50]}... - {self.author}"

class MoodEntry(models.Model):
    MOOD_CHOICES = [
        ('happy', '😊 Happy'),
        ('fear', '😨 Fear'),
        ('sad', '😔 Sad'),
        ('angry', '😠 Angry'),
        ('sick', '🤢 Sick'),
        
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.mood}"
    
    # ← ADD THIS METHOD
    def get_mood_display(self):
        """Returns the human-readable label with emoji, e.g. '😊 Happy'"""
        return dict(self.MOOD_CHOICES).get(self.mood, self.mood)



class DailyMove(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    date = models.DateField(unique=True)  # one per day
    image_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ContentPost(models.Model):  # Popular / feed items
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    author = models.CharField(max_length=100, blank=True)
    likes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_featured = models.BooleanField(default=False)


# models.py
class GeneratedQuote(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    mood = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateField(auto_now_add=True) # Note: DateField, not DateTimeField

    class Meta:
        # Ensures a user only has one entry per day for a specific mood
        unique_together = ('user', 'mood', 'created_at')
        
        
from cloudinary.models import CloudinaryField

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Product Image via Cloudinary
    image = CloudinaryField('image', folder='products/', null=True, blank=True)
    
    # External link to purchase (if applicable)
    buy_url = models.URLField(max_length=500, blank=True, null=True)
    
    is_active = models.BooleanField(default=True, help_text="Designates whether this product should be treated as active.")
    is_featured = models.BooleanField(default=False, help_text="Show this product in the 'Featured' section of the home page.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

from .tasks import send_bulk_product_notification 

from django.db import transaction


@receiver(post_save, sender=Product)
def trigger_product_notification(sender, instance, created, **kwargs):
    """
    Signal only triggers the Celery task. 
    It does NOT loop through users here.
    """
    if instance.is_featured and instance.is_active:
        # transaction.on_commit ensures the task runs AFTER the DB save is 100% complete
        def trigger_task():
            try:
                send_bulk_product_notification.delay(instance.id)
            except Exception as e:
                logger.warning(f"Failed to queue product notification task for product {instance.id}: {e}")
        
        transaction.on_commit(trigger_task)

class TabathaPrompt(models.Model):
    """Stores the system prompt used by Gemini to generate Tabatha's daily message."""
    text = models.TextField(help_text="System prompt to guide the AI for Tabatha's daily message.")
    is_active = models.BooleanField(default=False, help_text="Only one prompt should be active at a time.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        status = "(Active)" if self.is_active else "(Inactive)"
        return f"Tabatha Prompt {self.id} {status}"
        
class TabathaDailyMessage(models.Model):
    """Stores the generated daily message for all users."""
    date = models.DateField(unique=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Tabatha's Message for {self.date}"