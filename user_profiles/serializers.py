from rest_framework import serializers
from accounts.models import CustomUser
from .models import UserProfile
from spiritual.models import VideoTrack  # for saved spiritual
from journal.models import JournalEntry   # for journal archive


def force_https_url(url):
    if not url:
        return url

    if url.startswith('//'):
        return f"https:{url}"

    if url.startswith('http://'):
        return url.replace('http://', 'https://', 1)

    return url

class UserProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True)  # Allow update
    

    # Using ImageField for the upload, URL for the response
    profile_picture = serializers.ImageField(write_only=True, required=False)
    profile_picture_url = serializers.SerializerMethodField()
    
    # Map properties clearly
    current_mood = serializers.ReadOnlyField()
    current_mood_display = serializers.ReadOnlyField()

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'full_name',
            'email',
            'phone_number',
            'profile_picture',
            'profile_picture_url',
            'notifications_enabled',
            'current_mood',
            'current_mood_display',
            'member_since'
        ]
        read_only_fields = ['email', 'current_mood', 'current_mood_display', 'member_since', 'profile_picture']

    # def get_profile_picture_url(self, obj):
    #     if obj.profile_picture:
    #         return obj.profile_picture.url
    #     return None
    
    
    def get_profile_picture_url(self, obj):
        # Prefer social profile picture URL (from Google/Apple) over uploaded ones
        if obj.social_profile_picture_url:
            return force_https_url(obj.social_profile_picture_url)
        
        if obj.profile_picture:
            # Check if it's already a URL or a CloudinaryResource
            if hasattr(obj.profile_picture, 'url'):
                return force_https_url(obj.profile_picture.url)
            return force_https_url(str(obj.profile_picture))
        return None

    def update(self, instance, validated_data):
        # CloudinaryField handles the file object directly
        profile_pic = validated_data.pop('profile_picture', None)
        if profile_pic:
            instance.profile_picture = profile_pic
            
        # Update other fields automatically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance
    

    # def update(self, instance, validated_data):
    #     if 'profile_picture' in validated_data:
    #         instance.profile_picture = validated_data.pop('profile_picture')
    #     instance.full_name = validated_data.get('full_name', instance.full_name)
    #     instance.phone_number = validated_data.get('phone_number', instance.phone_number)
    #     instance.notifications_enabled = validated_data.get('notifications_enabled', instance.notifications_enabled)
    #     instance.save()
    #     return instance



# user_profiles/serializers.py

class UserPublicSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_picture_url = serializers.SerializerMethodField()
    id = serializers.IntegerField(source='user.id', read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        # Only include public-facing fields
        fields = ['id', 'full_name', 'email', 'profile_picture_url','is_following']

    def get_profile_picture_url(self, obj):
        # Prefer social profile picture URL (from Google/Apple) over uploaded ones
        if obj.social_profile_picture_url:
            return force_https_url(obj.social_profile_picture_url)
        
        if obj.profile_picture:
            return force_https_url(obj.profile_picture.url)
        return None
    def get_is_following(self, obj):
        # Since this is for the "Following" list, this is always True
        return True



class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

class SavedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoTrack
        fields = ['id', 'title', 'cover_url', 'duration_seconds', 'created_at']

class JournalArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalEntry
        fields = ['id', 'content', 'mood', 'created_at', 'ai_insight']
        


# # user_profiles/serializers.py
# from rest_framework import serializers
# from .models import UserProfile
# from spiritual.models import VideoTrack
# from journal.models import JournalEntry


# class UserProfileSerializer(serializers.ModelSerializer):
#     email = serializers.EmailField(source='user.email', read_only=True)
#     full_name = serializers.CharField(required=False, allow_blank=True)  # Writable

#     # Image field to accept file upload
#     profile_picture = serializers.ImageField(write_only=True, required=False)

#     # Read-only URL (from Cloudinary or local)
#     profile_picture_url = serializers.SerializerMethodField(read_only=True)

#     class Meta:
#         model = UserProfile
#         fields = [
#             'full_name',
#             'email',
#             'phone_number',
#             'profile_picture',          # For upload (write_only)
#             'profile_picture_url',      # For display (read_only)
#             'notifications_enabled',
#             'current_mood',
#             'current_mood_display',
#             'member_since'
#         ]
#         read_only_fields = [
#             'email',
#             'current_mood_display',
#             'member_since',
#             'profile_picture_url'       # Generated automatically
#         ]

#     def get_profile_picture_url(self, obj):
#         """Return Cloudinary URL or local URL"""
#         if obj.profile_picture:
#             request = self.context.get('request')
#             if request:
#                 return request.build_absolute_uri(obj.profile_picture.url)
#             return obj.profile_picture.url
#         return None

#     def update(self, instance, validated_data):
#         # Handle profile picture upload
#         if 'profile_picture' in validated_data:
#             instance.profile_picture = validated_data.pop('profile_picture')

#         # Update other fields
#         instance.full_name = validated_data.get('full_name', instance.full_name)
#         instance.phone_number = validated_data.get('phone_number', instance.phone_number)
#         instance.notifications_enabled = validated_data.get(
#             'notifications_enabled', instance.notifications_enabled
#         )

#         instance.save()
#         return instance


# class ChangePasswordSerializer(serializers.Serializer):
#     old_password = serializers.CharField(required=True, write_only=True)
#     new_password = serializers.CharField(required=True, write_only=True)
#     confirm_password = serializers.CharField(required=True, write_only=True)

#     def validate(self, data):
#         if data['new_password'] != data['confirm_password']:
#             raise serializers.ValidationError("Passwords do not match.")
#         return data

#     def validate_old_password(self, value):
#         user = self.context['request'].user
#         if not user.check_password(value):
#             raise serializers.ValidationError("Old password is incorrect.")
#         return value


# class SavedVideoSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = VideoTrack
#         fields = ['id', 'title', 'cover_url', 'duration_seconds', 'created_at']


# class JournalArchiveSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = JournalEntry
#         fields = ['id', 'content', 'mood', 'created_at', 'ai_insight']
