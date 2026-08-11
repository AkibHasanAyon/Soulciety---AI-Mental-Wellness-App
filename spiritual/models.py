# spiritual/models.py
import cloudinary.api
import cloudinary.uploader
from cloudinary.models import CloudinaryField
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
from django.db import models, transaction # Added transaction
from .tasks import send_new_content_push, update_video_metadata # Import the new task
import logging

logger = logging.getLogger(__name__)

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class VideoTrack(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # --- Cloudinary Fields ---
    # resource_type='video' is essential for videos
    video_file = CloudinaryField('video', resource_type='video', folder='videos/', null=True, blank=True)
    thumbnail_url = CloudinaryField('thumbnail_image', folder='thumbnails/', null=True, blank=True)
    
    # --- Metadata ---
    duration_seconds = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    # --- Relationships & Flags ---
    categories = models.ManyToManyField(Category, related_name='videos')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
            # 1. Check if we are replacing an existing video file
            if self.pk:
                old_instance = VideoTrack.objects.filter(pk=self.pk).first()
                if old_instance and old_instance.video_file != self.video_file:
                    # File changed! Reset duration so it's re-calculated for the new file
                    self.duration_seconds = 0

            # 2. OPTIMIZATION: Try to get duration immediately from the upload response
            # This works if Cloudinary processed the small video instantly during upload
            if hasattr(self.video_file, 'metadata'):
                metadata = self.video_file.metadata
                if metadata and 'duration' in metadata:
                    self.duration_seconds = int(round(float(metadata['duration'])))

            # 3. Standard Django Save
            super().save(*args, **kwargs)

            # 4. RELIABILITY: If duration is still 0, trigger Celery to fetch it 
            # This handles larger videos that Cloudinary processes asynchronously
            if self.video_file and self.duration_seconds == 0:
                # transaction.on_commit ensures the task starts AFTER the DB is finished
                def trigger_metadata_task():
                    try:
                        update_video_metadata.delay(self.id)
                    except Exception as e:
                        logger.warning(f"Failed to queue video metadata update task for video {self.id}: {e}")
                
                transaction.on_commit(trigger_metadata_task)
                
    def delete_assets(self):
        """Helper method to clean up Cloudinary assets"""
        if self.video_file:
            try:
                # IMPORTANT: videos must specify resource_type="video"
                cloudinary.uploader.destroy(self.video_file.public_id, resource_type="video")
            except Exception as e:
                print(f"Error deleting video: {e}")
        
        if self.thumbnail_url:
            try:
                # Images use the default resource_type="image"
                cloudinary.uploader.destroy(self.thumbnail_url.public_id)
            except Exception as e:
                print(f"Error deleting thumbnail: {e}")

    def delete(self, *args, **kwargs):
        # Trigger cleanup for single-item delete
        self.delete_assets()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title

class SuggestedVideo(models.Model):
    video = models.ForeignKey(VideoTrack, on_delete=models.CASCADE)
    priority = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-priority']

    def __str__(self):
        return f"Suggested: {self.video.title}"

class UserFavoriteVideo(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    video = models.ForeignKey(VideoTrack, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')
        
        
        
# spiritual/models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import VideoTrack
from notifications.helpers import create_notification
from accounts.models import CustomUser

@receiver(post_save, sender=VideoTrack)
def notify_new_video(sender, instance, created, **kwargs):
    """
    When a new video is uploaded and set to active, notify all users.
    """
    if created and instance.is_active:
        # We use a task for this to avoid slowing down the admin panel upload
        try:
            send_new_content_push.delay(instance.id)
        except Exception as e:
            logger.warning(f"Failed to queue new content push task for video {instance.id}: {e}")