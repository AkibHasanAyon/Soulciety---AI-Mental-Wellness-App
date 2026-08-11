from django.urls import path
from .views import (
    ConversationListCreateView, ConversationDetailView,
    MessageListCreateView,LatestMessageView
)

urlpatterns = [
    # ── Chat Feature ──
    path('chat/conversations/', ConversationListCreateView.as_view(), name='chat-conversations'),
    path('chat/conversations/<int:pk>/', ConversationDetailView.as_view(), name='chat-conversation-detail'),
    path('chat/conversations/<int:conversation_id>/messages/', MessageListCreateView.as_view(), name='chat-messages'),
    path('chat/conversations/<int:conversation_id>/messages/latest/', LatestMessageView.as_view()),
    
]   