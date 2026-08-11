# pyrefly: ignore [missing-import]
from rest_framework import serializers
from .models import JournalEntry

class JournalEntrySerializer(serializers.ModelSerializer):
    # Use SerializerMethodField for has_insight as we discussed earlier 
    # to avoid the 'False' response issue.
    has_insight = serializers.SerializerMethodField()
    insight_status = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'content', 'mood', 'tags', 'created_at', 'updated_at',
            'ai_insight', 'insight_generated_at', 'is_private', 
            'has_insight', 'is_archived', 'insight_status'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'ai_insight', 
            'insight_generated_at', 'is_archived'
        ]
        
    def get_has_insight(self, obj):
        return bool(obj.ai_insight and "Reflecting on your thoughts" not in obj.ai_insight)
    
    def get_insight_status(self, obj):
        """Returns: 'ready', 'processing', or 'pending'"""
        if obj.ai_insight and "Reflecting on your thoughts" not in obj.ai_insight and "Regenerating" not in obj.ai_insight:
            return 'ready'
        elif obj.ai_insight:
            return 'processing'
        return 'pending'

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class JournalEntryListSerializer(serializers.ModelSerializer):
    has_insight = serializers.SerializerMethodField()
    insight_status = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = ['id', 'mood', 'content', 'created_at', 'ai_insight', 'tags', 'has_insight', 'is_archived', 'insight_status']

    def get_has_insight(self, obj):
        return bool(obj.ai_insight and "Reflecting on your thoughts" not in obj.ai_insight)
    
    def get_insight_status(self, obj):
        """Returns: 'ready', 'processing', or 'pending'"""
        if obj.ai_insight and "Reflecting on your thoughts" not in obj.ai_insight and "Regenerating" not in obj.ai_insight:
            return 'ready'
        elif obj.ai_insight:
            return 'processing'
        return 'pending'