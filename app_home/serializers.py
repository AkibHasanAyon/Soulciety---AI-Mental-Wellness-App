from rest_framework import serializers
from .models import Quote, MoodEntry, DailyMove, ContentPost, Product
from django.utils import timezone

class QuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quote
        fields = ['id', 'text', 'author']

class MoodEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = MoodEntry
        fields = ['id', 'mood', 'note', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class DailyMoveSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyMove
        fields = ['id', 'title', 'description', 'date', 'image_url']

class ContentPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentPost
        fields = ['id', 'title', 'description', 'image_url', 'author', 'likes_count']
        
# app_home/serializers.py
from rest_framework import serializers
from .models import Product

class ProductSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 
            'image', 'image_url', 'buy_url', 'is_featured'
        ]
        # 'image' is write_only so we don't send the raw Cloudinary object to the app
        extra_kwargs = {'image': {'write_only': True}}

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url.replace("http", "https")
        return None