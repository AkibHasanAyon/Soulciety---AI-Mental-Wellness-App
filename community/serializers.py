from rest_framework import serializers

# from user_profiles.serializers import UserProfileSerializer
from .models import CommunityPost, Like, Comment, Follow, DailyPrompt
from accounts.models import CustomUser

# community/serializers.py
from user_profiles.serializers import UserPublicSerializer


def force_https_url(url):
    if not url:
        return url

    if url.startswith('//'):
        return f"https:{url}"

    if url.startswith('http://'):
        return url.replace('http://', 'https://', 1)

    return url

class CommentSerializer(serializers.ModelSerializer):
    # Show name/photo of the person who commented
    user = UserPublicSerializer(source='user.profile', read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']



class LikeSerializer(serializers.ModelSerializer):
    # Show the public profile of the person who liked the post
    user = UserPublicSerializer(source='user.profile')

    class Meta:
        model = Like
        fields = ['user', 'created_at']


from .models import Like

class CommunityPostSerializer(serializers.ModelSerializer):
    user = UserPublicSerializer(source='user.profile',  read_only=True)
    likes_count = serializers.ReadOnlyField()

    
    # user_email = serializers.EmailField(source='user.email', read_only=True)  
    image_url = serializers.SerializerMethodField()
    
    # 2. Nested List of Likes (Uses the LikeSerializer above)
    likes = LikeSerializer(many=True, read_only=True)
    
    # 3. Dynamic count of likes
    likes_count = serializers.IntegerField(source='likes.count', read_only=True)
    
    # Accept image upload
    # image = serializers.ImageField(write_only=True, required=False)
    
    # Return Cloudinary URL
    # image_url = serializers.SerializerMethodField()

    class Meta: 
        model = CommunityPost
        fields = [
            'id', 
            'user', 
            'content', 
            'image',           # write_only for upload
            'image_url',       # read_only for display
            'likes',           # The list of who liked it
            'likes_count',     # The total number
            'comments_count', 
            'created_at'
        ]
               
        extra_kwargs = {'image': {'write_only': True}}

    def get_image_url(self, obj):
        if obj.image:
            return force_https_url(obj.image.url)
        return None
    

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    
    
class PostDetailSerializer(CommunityPostSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = CommunityPost
        fields = CommunityPostSerializer.Meta.fields + ['comments']


class PostReportCreateSerializer(serializers.Serializer):
    post_id = serializers.IntegerField()
    reason = serializers.CharField()

    def validate_reason(self, value):
        cleaned_value = value.strip()
        if not cleaned_value:
            raise serializers.ValidationError("Reason is required.")
        return cleaned_value


class DailyPromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyPrompt
        fields = ['id', 'text', 'category', 'last_used_at']
