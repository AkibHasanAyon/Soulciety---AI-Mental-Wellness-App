# memory/admin.py
# pyrefly: ignore [missing-import]
from django.contrib import admin
from .models import UserMemory, ConversationSummary, MemoryExtractionLog


@admin.register(UserMemory)
class UserMemoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'key', 'value_preview', 'confidence', 'is_active', 'updated_at')
    list_filter = ('category', 'is_active', 'confidence')
    search_fields = ('user__email', 'key', 'value')
    list_editable = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-updated_at',)

    def value_preview(self, obj):
        return obj.value[:80] + '...' if len(obj.value) > 80 else obj.value
    value_preview.short_description = 'Value'


@admin.register(ConversationSummary)
class ConversationSummaryAdmin(admin.ModelAdmin):
    list_display = ('user', 'conversation', 'emotional_state', 'message_count_at_summary', 'updated_at')
    list_filter = ('emotional_state',)
    search_fields = ('user__email', 'summary_text')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemoryExtractionLog)
class MemoryExtractionLogAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'messages_processed', 'memories_extracted', 'processed_at')
    readonly_fields = ('processed_at',)
    ordering = ('-processed_at',)
