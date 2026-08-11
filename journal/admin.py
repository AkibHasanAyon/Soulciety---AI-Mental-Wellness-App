from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import JournalEntry

@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'mood', 'ai_insight_preview')
    list_filter = ('created_at', 'mood')
    search_fields = ('content', 'ai_insight')
    readonly_fields = ('created_at', 'updated_at', 'insight_generated_at')

    def ai_insight_preview(self, obj):
        return obj.ai_insight[:50] + "..." if obj.ai_insight else ""
    ai_insight_preview.short_description = "AI Insight"