# memory/tasks.py
"""
Celery tasks for async memory extraction and conversation summarization.
"""
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def extract_and_store_memories(self, conversation_id):
    """
    Extract important user facts from a conversation and store them.
    Triggered after each AI response generation.
    """
    try:
        from chat.models import ChatConversation
        from .models import UserMemory, MemoryExtractionLog
        from .extractor import extract_memories
        from .vector_store import store_memory

        conversation = ChatConversation.objects.get(id=conversation_id)
        user = conversation.user

        # Get the last extraction log to know where we left off
        last_log = MemoryExtractionLog.objects.filter(
            conversation=conversation
        ).order_by('-processed_at').first()

        last_processed_count = last_log.messages_processed if last_log else 0

        # Get messages since last extraction (or all if first time)
        all_messages = list(
            conversation.messages.order_by('created_at')
        )
        current_count = len(all_messages)

        # Only process if there are enough new messages (at least 10 — 5 turns)
        if current_count - last_processed_count < 10:
            return {"skipped": True, "reason": "Not enough new messages"}

        # Get messages to process (since last extraction + overlap for context)
        messages_to_process = all_messages[max(0, last_processed_count - 2):]  # overlap for context
        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages_to_process
        ]

        # Get existing memories for deduplication
        existing = list(
            UserMemory.objects.filter(user=user, is_active=True)
            .values_list('key', 'value')
        )
        existing_strings = [f"{k}: {v}" for k, v in existing]

        # Extract memories using LLM
        result = extract_memories(message_dicts, existing_memories=existing_strings)

        if not result:
            logger.warning(f"Memory extraction returned no result for conv {conversation_id}")
            return {"extracted": 0}

        memories_count = 0

        # Store extracted facts
        for fact in result.get('facts', []):
            category = fact.get('category', 'patterns')
            key = fact.get('key', '')
            value = fact.get('value', '')
            confidence = fact.get('confidence', 0.8)

            if not key or not value:
                continue

            # Upsert: update if exists, create if not
            memory, created = UserMemory.objects.update_or_create(
                user=user,
                category=category,
                key=key,
                defaults={
                    'value': value,
                    'confidence': confidence,
                    'source_conversation': conversation,
                    'is_active': True,
                }
            )

            # Store in vector DB for semantic search
            memory_text = f"{key.replace('_', ' ')}: {value}"
            store_memory(
                user_id=user.id,
                memory_id=f"memory_{memory.id}",
                text=memory_text,
                metadata={
                    'category': category,
                    'key': key,
                    'conversation_id': conversation_id,
                }
            )
            memories_count += 1

        # Log the extraction
        MemoryExtractionLog.objects.create(
            conversation=conversation,
            messages_processed=current_count,
            memories_extracted=memories_count,
        )

        # Also trigger a conversation summary update if needed
        if result.get('summary_update') or result.get('emotional_state'):
            _update_conversation_summary(
                conversation=conversation,
                user=user,
                summary_text=result.get('summary_update', ''),
                emotional_state=result.get('emotional_state', ''),
                key_topics=result.get('key_topics', []),
                message_count=current_count,
            )

        logger.info(
            f"Memory extraction for conv {conversation_id}: "
            f"{memories_count} facts stored"
        )
        return {"extracted": memories_count}

    except Exception as exc:
        logger.error(f"Memory extraction failed for conv {conversation_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=15)
def generate_conversation_summary(self, conversation_id):
    """
    Generate or update a conversation summary.
    Called periodically (every ~10 messages) or when a conversation ends.
    """
    try:
        from chat.models import ChatConversation
        from .models import ConversationSummary
        from .extractor import extract_memories

        conversation = ChatConversation.objects.get(id=conversation_id)
        user = conversation.user

        # Get all messages
        messages = list(conversation.messages.order_by('created_at'))
        if len(messages) < 3:
            return {"skipped": True, "reason": "Too few messages"}

        message_dicts = [
            {"role": msg.role, "content": msg.content}
            for msg in messages[-20:]  # last 20 messages for summary
        ]

        result = extract_memories(message_dicts)
        if not result:
            return {"skipped": True, "reason": "Extraction failed"}

        _update_conversation_summary(
            conversation=conversation,
            user=user,
            summary_text=result.get('summary_update', ''),
            emotional_state=result.get('emotional_state', ''),
            key_topics=result.get('key_topics', []),
            message_count=len(messages),
        )

        return {"summary": result.get('summary_update', '')}

    except Exception as exc:
        logger.error(f"Summary generation failed for conv {conversation_id}: {exc}")
        raise self.retry(exc=exc)


def _update_conversation_summary(conversation, user, summary_text, emotional_state, key_topics, message_count):
    """Helper to create or update a ConversationSummary."""
    from .models import ConversationSummary

    summary, created = ConversationSummary.objects.update_or_create(
        conversation=conversation,
        defaults={
            'user': user,
            'summary_text': summary_text,
            'emotional_state': emotional_state,
            'key_topics': key_topics,
            'message_count_at_summary': message_count,
        }
    )
    return summary
