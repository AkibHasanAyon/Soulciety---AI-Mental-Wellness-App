from rest_framework import serializers
from .models import ChatConversation, ChatMessage

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'created_at']

class ChatConversationSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'last_message', 'message_count']

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        return ChatMessageSerializer(last_msg).data if last_msg else None

    def get_message_count(self, obj):
        return obj.messages.count()