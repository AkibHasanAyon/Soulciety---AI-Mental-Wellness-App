from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings
from accounts.models import CustomUser
from cloudinary.models import CloudinaryField
import cloudinary.uploader # Import the uploader

class CommunityPost(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='community_posts')
    content = models.TextField(blank=True)  # main text
    # image = models.ImageField(upload_to='community/posts/', blank=True, null=True)
        # Updated for Cloudinary
    image = CloudinaryField(
        'image', 
        folder='community/posts/', 
        blank=True, 
        null=True
    )
    
    # image_url = models.URLField(blank=True, null=True)  # for Cloudinary later
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    def delete(self, *args, **kwargs):
        if self.image:
            # Community posts use images, so resource_type defaults to "image"
            cloudinary.uploader.destroy(self.image.public_id)
        
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} - {self.content[:50]}..."

    class Meta:
        ordering = ['-created_at']

class Like(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

class Comment(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']

class Follow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')


class PostReport(models.Model):
    reporter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='reported_posts'
    )
    post = models.ForeignKey(
        CommunityPost,
        on_delete=models.SET_NULL,
        related_name='reports',
        null=True,
        blank=True
    )
    reported_post_id = models.PositiveIntegerField()
    reason = models.TextField()
    post_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.email} on post {self.reported_post_id}"


class DailyPrompt(models.Model):
    """Curated bank of conversation prompts posted daily by the AI system."""

    CATEGORY_CHOICES = [
        ('self-reflection', 'Self Reflection'),
        ('growth', 'Growth'),
        ('healing', 'Healing'),
        ('mindset', 'Mindset'),
        ('gratitude', 'Gratitude'),
        ('vision', 'Vision'),
    ]

    text = models.TextField(help_text="The prompt question, e.g. 'What cycle are you breaking?'")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, blank=True)
    is_active = models.BooleanField(default=True)
    times_used = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_used_at', 'times_used']  # least-recently-used first

    def __str__(self):
        return self.text[:80]