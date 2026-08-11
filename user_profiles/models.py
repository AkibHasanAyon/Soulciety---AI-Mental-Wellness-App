#user_profiles/models.py
from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
from django.utils import timezone
from app_home.models import MoodEntry
from cloudinary.models import CloudinaryField
import cloudinary.uploader # Import the uploader

# user_profiles/models.py
from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from app_home.models import MoodEntry  # Adjust import path if MoodEntry is in different app

class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    # profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    profile_picture = CloudinaryField('image', folder='profile_pictures/', blank=True, null=True)
    # profile_picture_url = models.URLField(blank=True, null=True)
    social_profile_picture_url = models.URLField(blank=True, null=True)  # For Google/Apple profile images
    phone_number = models.CharField(max_length=20, blank=True)
    notifications_enabled = models.BooleanField(default=True)
    member_since = models.DateTimeField(default=timezone.now, editable=False)
    full_name = models.CharField(max_length=255, blank=True)
    
    # Example for UserProfile save method
    def save(self, *args, **kwargs):
            if self.id:
                old_instance = UserProfile.objects.get(id=self.id)
                # If the profile picture is being changed
                if old_instance.profile_picture and self.profile_picture != old_instance.profile_picture:
                    cloudinary.uploader.destroy(old_instance.profile_picture.public_id)
            
            super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.profile_picture:
            cloudinary.uploader.destroy(self.profile_picture.public_id)
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email}'s Profile"

    # ── Current Mood from Latest MoodEntry ──
    @property
    def current_mood(self):
        """Returns the mood key (e.g., 'happy') from the latest MoodEntry"""
        latest = MoodEntry.objects.filter(user=self.user).order_by('-created_at').first()
        return latest.mood if latest else None

    @property
    def current_mood_display(self):
        """Returns the pretty label with emoji (e.g., '😊 Happy')"""
        latest = MoodEntry.objects.filter(user=self.user).order_by('-created_at').first()
        if latest:
            return latest.get_mood_display()
        return "No mood recorded yet"
    





# Signal to auto-create profile when user is created
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()