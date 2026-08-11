# pyrefly: ignore-errors


from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
import logging
from .models import ChatConversation, ChatMessage
from .serializers import ChatConversationSerializer, ChatMessageSerializer
from django.db import transaction
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

logger = logging.getLogger(__name__)


def get_user_key(group, request):
    """Custom key function for rate limiting based on user ID"""
    if request.user.is_authenticated:
        return f"user_{request.user.id}"
    return request.META.get('REMOTE_ADDR', 'unknown')




# ── Chat Conversation Endpoints ──
class ConversationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 1. Filter by is_active so "deleted" chats don't show up in history
        conversations = ChatConversation.objects.filter(user=request.user, is_active=True)
        serializer = ChatConversationSerializer(conversations, many=True)
        return Response(serializer.data)

    def post(self, request):
        with transaction.atomic():
            conversation = ChatConversation.objects.create(
                user=request.user,
                title="New Conversation"
            )
            
        serializer = ChatConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    




class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return ChatConversation.objects.get(pk=pk, user=request.user)
        except ChatConversation.DoesNotExist:
            return None

    def get(self, request, pk):
        conv = self.get_object(request, pk)
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = ChatConversationSerializer(conv)
        return Response(serializer.data)

    def delete(self, request, pk):
        conv = self.get_object(request, pk)
        if not conv:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



from .tasks import generate_ai_response

# chat/views.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import GenericAPIView # Import this

class ChatMessagePagination(PageNumberPagination):
    page_size = 20  # Number of messages per page
    page_size_query_param = 'page_size'
    max_page_size = 50

class MessageListCreateView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = ChatMessagePagination
    serializer_class = ChatMessageSerializer

    def get(self, request, conversation_id):
        try:
            conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
        except ChatConversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)
        
        messages = conversation.messages.order_by('created_at')
        
        # GenericAPIView provides paginate_queryset
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @method_decorator(ratelimit(key=get_user_key, rate='30000000/d', block=False))
    def post(self, request, conversation_id):
        # Check if rate limited
        was_limited = getattr(request, 'limited', False)
        logger.info(f"Chat Message POST - User: {request.user.id}, Limited: {was_limited}")
        
        if was_limited:
            logger.warning(f"User {request.user.id} exceeded chat message rate limit")
            return Response(
                {
                    "error": "Daily message limit reached",
                    "detail": "You can send up to 10 AI messages per day. Please try again tomorrow.",
                    "limit": "10/day"
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        try:
            conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
        except ChatConversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=status.HTTP_404_NOT_FOUND)

        content = request.data.get('content', '').strip()
        if not content:
            return Response({"error": "Message content is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Save user message
        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role='user',
            content=content
        )

        # 5. FIX: Trigger AI response ONLY after DB commit with error handling
        def trigger_ai_task():
            try:
                generate_ai_response.delay(conversation_id, content)
            except Exception as e:
                logger.warning(f"Failed to queue AI response task for conversation {conversation_id}: {e}")
        
        transaction.on_commit(trigger_ai_task)

        # Update timestamp
        conversation.updated_at = timezone.now()
        conversation.save()

        return Response({
            "message": "Message sent. Soulciety AI is reflecting on your words...",
            "user_message": ChatMessageSerializer(user_message).data,
            "ai_thinking": True
        }, status=status.HTTP_202_ACCEPTED)


# # chat/views.py
class LatestMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id):
        try:
            conversation = ChatConversation.objects.get(id=conversation_id, user=request.user)
        except ChatConversation.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        latest = conversation.messages.order_by('-created_at').first()
        if latest:
            return Response(ChatMessageSerializer(latest).data)
        return Response({"message": "No messages yet"}) 