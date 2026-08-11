  
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.utils.decorators import method_decorator
import logging
from .models import JournalEntry
from .serializers import JournalEntrySerializer, JournalEntryListSerializer
from .tasks import generate_ai_insight
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited
from rest_framework.views import exception_handler
logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    if isinstance(exc, Ratelimited):
        return Response(
            {
                "error": "Too Many Requests",
                "detail": "Rate limit exceeded. Try again later."
            },
            status=429
        )
 
    # fall back to DRF's default handler for everything else
    return exception_handler(exc, context)

class JournalEntryDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return JournalEntry.objects.get(pk=pk, user=user)
        except JournalEntry.DoesNotExist:
            return None

    def get(self, request, pk):
        entry = self.get_object(pk, request.user)
        if not entry:
            return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = JournalEntrySerializer(entry)
        return Response(serializer.data)

    def put(self, request, pk):
        entry = self.get_object(pk, request.user)
        if not entry:
            return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if content is actually changing to decide if we need a new AI insight
        old_content = entry.content
        serializer = JournalEntrySerializer(entry, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            new_content = serializer.validated_data.get('content', old_content)
            
            if new_content != old_content:
                # Content changed: Reset insight and re-trigger AI
                entry = serializer.save(
                    ai_insight="✨ AI Insight: Regenerating based on your changes...",
                    has_insight=False
                )
                
                # Gracefully handle cases where Redis/Celery is unavailable
                def trigger_ai_task():
                    try:
                        generate_ai_insight.delay(entry.id)
                    except Exception as e:
                        logger.warning(f"Failed to queue AI insight task for entry {entry.id}: {e}")
                
                transaction.on_commit(trigger_ai_task)
            else:
                # Just metadata changed (tags/mood), no need to call Gemini
                entry = serializer.save()

            return Response(JournalEntrySerializer(entry).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        entry = self.get_object(pk, request.user)
        if not entry:
            return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)
        entry.delete()
        return Response({"message": "Entry deleted"}, status=status.HTTP_204_NO_CONTENT)


class JournalEntryListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Filter by is_archived=False so the main feed is "clean"
        entries = JournalEntry.objects.filter(
            user=request.user, 
            is_archived=False
        ).order_by('-created_at')
        
        serializer = JournalEntryListSerializer(entries, many=True)
        return Response(serializer.data)
    
    @method_decorator(ratelimit(key='user', rate='3/d', method='POST', block=True))
    def post(self, request):
        # Check if rate limited (django-ratelimit will raise Ratelimited if exceeded)
        # The decorator handles this automatically, but we catch it to return a custom message
        was_limited = getattr(request, 'limited', False)
        if was_limited:
            return Response(
                {
                    "error": "Daily journal limit reached. You can create up to 3 journals per day.",
                    "detail": "Rate limit exceeded. Please try again tomorrow."
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        serializer = JournalEntrySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # 1. Save with placeholder
            entry = serializer.save(
                ai_insight="✨ AI Insight: Reflecting on your thoughts...", 
                has_insight=False
            )
            
            # 2. Trigger AI task ONLY after the database transaction is committed
            # Gracefully handle cases where Redis/Celery is unavailable
            def trigger_ai_task():
                try:
                    generate_ai_insight.delay(entry.id)
                except Exception as e:
                    logger.warning(f"Failed to queue AI insight task for entry {entry.id}: {e}")
            
            transaction.on_commit(trigger_ai_task)

            return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JournalArchiveToggleView(APIView):
    """
    POST /api/journal/entries/<pk>/archive/
    Hides the entry from the main list.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            entry = JournalEntry.objects.get(pk=pk, user=request.user)
            # Toggle the archive status
            entry.is_archived = not entry.is_archived
            entry.save(update_fields=['is_archived'])
            
            status_msg = "archived" if entry.is_archived else "unarchived"
            return Response({
                "id": entry.id,
                "is_archived": entry.is_archived,
                "message": f"Journal entry {status_msg} successfully."
            }, status=status.HTTP_200_OK)
            
        except JournalEntry.DoesNotExist:
            return Response({"error": "Entry not found"}, status=status.HTTP_404_NOT_FOUND)


class JournalArchivedListView(APIView):
    """
    GET /api/   archived/
    Shows only the hidden/archived entries.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch only archived entries
        archived_entries = JournalEntry.objects.filter(
            user=request.user, 
            is_archived=True
        ).order_by('-created_at')
        
        serializer = JournalEntryListSerializer(archived_entries, many=True)
        return Response(serializer.data)