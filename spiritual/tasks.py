# spiritual/tasks.py
from celery import shared_task
import cloudinary.api
from django.apps import apps
import logging

from accounts.models import CustomUser
from notifications.helpers import create_notification




logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=10, default_retry_delay=30)
def update_video_metadata(self, video_id):
    VideoTrack = apps.get_model('spiritual', 'VideoTrack')
    
    # FIX: Use .filter().first() instead of .get()
    # If the video was deleted, this returns None instead of crashing
    video = VideoTrack.objects.filter(id=video_id).first()
    
    if not video:
        return f"Task aborted: Video {video_id} no longer exists in database."

    try:
        # Fetch metadata using the Admin API
        res = cloudinary.api.resource(
            video.video_file.public_id, 
            resource_type="video",
            image_metadata=True 
        )
        
        # Look for duration in all possible Cloudinary response locations
        duration = (
            res.get('duration') or 
            res.get('video_duration') or 
            res.get('media_metadata', {}).get('duration')
        )

        if duration:
            actual_duration = int(round(float(duration)))
            # Update only the specific field to avoid overwriting other user edits
            VideoTrack.objects.filter(id=video_id).update(duration_seconds=actual_duration)
            return f"Success: {video.title} updated to {actual_duration}s"
        
        raise Exception("Duration not yet processed by Cloudinary")

    except Exception as exc:
        logger.warning(f"Retrying metadata fetch for {video_id}: {exc}")
        raise self.retry(exc=exc)
    
    

# spiritual/tasks.py
@shared_task
def send_new_content_push(video_id):
    from .models import VideoTrack
    video = VideoTrack.objects.get(id=video_id)
    users = CustomUser.objects.filter(is_active=True, profile__notifications_enabled=True)
    
    for user in users:
        create_notification(
            user=user,
            title="🎥 New Healing Video",
            message=f"We just added '{video.title}'. Take a moment for yourself.",
            notif_type='new_content',
            data={"type": "video", "video_id": str(video.id)}
        )