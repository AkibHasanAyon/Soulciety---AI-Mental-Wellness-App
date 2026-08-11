# memory/models.py
# pyrefly: ignore [missing-import]
from django.db import models
from accounts.models import CustomUser
from chat.models import ChatConversation


class UserMemory(models.Model):
    """
    Stores extracted personal facts about the user.
    Each row = one key fact (e.g., "children" → "2 kids, ages 5 and 8").
    """
    CATEGORY_CHOICES = [
        ('identity', 'Core Identity'),
        ('family', 'Family & Relationships'),
        ('career', 'Career & Finances'),
        ('spiritual', 'Spiritual & Personal Growth'),
        ('emotional', 'Emotional & Mental Health'),
        ('exercises', 'Exercises & Practices'),
        ('patterns', 'Conversation Patterns'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='memories')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    key = models.CharField(max_length=100, help_text="e.g., children, career, manifestation_goals")
    value = models.TextField(help_text="The extracted fact value")
    confidence = models.FloatField(
        default=0.8,
        help_text="0.0–1.0 confidence score from extraction"
    )
    source_conversation = models.ForeignKey(
        ChatConversation, on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Conversation where this fact was extracted from"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, help_text="Soft delete for outdated facts")

    class Meta:
        unique_together = ('user', 'category', 'key')
        ordering = ['-updated_at']
        verbose_name_plural = 'User Memories'

    def __str__(self):
        return f"{self.user.email} — {self.category}/{self.key}: {self.value[:60]}"


class ConversationSummary(models.Model):
    """
    Stores a compressed summary of a conversation.
    Updated periodically as the conversation grows.
    """
    conversation = models.OneToOneField(
        ChatConversation, on_delete=models.CASCADE, related_name='summary'
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='conversation_summaries')
    summary_text = models.TextField(help_text="LLM-generated summary of the conversation")
    key_topics = models.JSONField(
        default=list, blank=True,
        help_text='e.g., ["startup stress", "self-worth"]'
    )
    emotional_state = models.CharField(
        max_length=50, blank=True,
        help_text="Dominant emotional state detected"
    )
    message_count_at_summary = models.PositiveIntegerField(
        default=0,
        help_text="Number of messages when this summary was last generated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Conversation Summaries'

    def __str__(self):
        return f"Summary for {self.conversation} — {self.emotional_state}"


class MemoryExtractionLog(models.Model):
    """
    Tracks memory extraction runs to avoid reprocessing.
    """
    conversation = models.ForeignKey(
        ChatConversation, on_delete=models.CASCADE, related_name='extraction_logs'
    )
    messages_processed = models.PositiveIntegerField(default=0)
    memories_extracted = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extraction for conv {self.conversation_id} — {self.memories_extracted} memories"
