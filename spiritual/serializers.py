from rest_framework import serializers
from .models import Category, VideoTrack, SuggestedVideo


# spiritual/serializers.py
from rest_framework import serializers
from .models import Category, VideoTrack, SuggestedVideo

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


# class VideoTrackSerializer(serializers.ModelSerializer):
#     categories = CategorySerializer(many=True, read_only=True)

#     # Accept file upload (write_only)
#     video_file = serializers.FileField(write_only=True, required=False)
#     thumbnail = serializers.ImageField(write_only=True, required=False)

#     # Return Cloudinary URLs (read_only)
#     video_url = serializers.SerializerMethodField()
#     thumbnail_url = serializers.SerializerMethodField()

#     class Meta:
#         model = VideoTrack
#         fields = [
#             'id', 'title', 'description',
#             'video_file', 'video_url',          # video_file for upload, video_url for display
#             'thumbnail', 'thumbnail_url',       # thumbnail for upload, thumbnail_url for display
#             'duration_seconds', 'categories',
#             'is_featured', 'created_at'
#         ]
#         read_only_fields = ['video_url', 'thumbnail_url', 'created_at']

#     def get_video_url(self, obj):
#         if obj.video_file:
#             return obj.video_file.url  # Cloudinary auto URL
#         return None

#     def get_thumbnail_url(self, obj):
#         if obj.thumbnail:
#             return obj.thumbnail.url  # Cloudinary auto URL
#         return None


# serializers.py
from rest_framework import serializers
from .models import VideoTrack
from .models import UserFavoriteVideo

# spiritual/serializers.py
class VideoTrackSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    duration_formatted = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField() # New Field
    

    class Meta:
        model = VideoTrack
        fields = [
            'id', 'title', 'description', 'video_url', 'thumbnail_url','duration_formatted', 'views_count', 'is_featured', 'created_at','is_bookmarked'
        ]

    def get_video_url(self, obj):
        return obj.video_file.url.replace("http", "https") if obj.video_file else None

    def get_thumbnail_url(self, obj):
        return obj.thumbnail_url.url.replace("http", "https") if obj.thumbnail_url else obj.thumbnail_url
    
    def get_duration_formatted(self, obj):
        if obj.duration_seconds:
            minutes = obj.duration_seconds // 60
            seconds = obj.duration_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return "00:00"
    
    # spiritual/serializers.py

    def get_is_bookmarked(self, obj):
        # Get the request safely
        request = self.context.get('request')
        
        # Check if request exists AND user is logged in
        if request and request.user and request.user.is_authenticated:
            return UserFavoriteVideo.objects.filter(user=request.user, video=obj).exists()
            
        return False




class SuggestedVideoSerializer(serializers.ModelSerializer):
    video = VideoTrackSerializer()

    class Meta:
        model = SuggestedVideo
        fields = ['id', 'video', 'priority']