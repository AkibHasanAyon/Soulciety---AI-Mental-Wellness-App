from django.contrib import admin
from django.utils.html import format_html
import json

from .models import (
    HealingAssessment,
    HealingJourneySettings,
    HealingTheme,
    HealingDay,
    DayContent,
    HealingStreak,
)


# ──────────────────────────────────────────────
# Inlines
# ──────────────────────────────────────────────

class HealingThemeInline(admin.TabularInline):
    model = HealingTheme
    extra = 0
    readonly_fields = ('day_number', 'theme_title', 'theme_intention', 'theme_category', 'healing_focus')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class DayContentInline(admin.StackedInline):
    model = DayContent
    extra = 0
    readonly_fields = (
        'generated_at', 'is_fallback', 'guided_reflection', 'affirmation',
        'mental_workout', 'physical_workout', 'breathing_exercise',
        'mini_challenge', 'journal_prompt',
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# HealingAssessment Admin
# ──────────────────────────────────────────────

@admin.register(HealingAssessment)
class HealingAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'status', 'is_archived',
        'journey_started_at', 'journey_completed_at', 'created_at',
    )
    list_filter = ('status', 'is_archived')
    search_fields = ('user__email',)
    readonly_fields = (
        'user', 'created_at', 'updated_at',
        'journey_started_at', 'journey_completed_at',
        'q1_emotional_baseline', 'q2_past_influence', 'q3_life_area_impact',
        'q4_core_pain_source', 'q5_coping_pattern', 'q6_relationship_fear',
        'q7_core_belief', 'q8_desired_relief', 'q9_healing_resistance',
        'q10_personal_desire',
        'healing_profile_display', 'generation_error',
    )
    inlines = [HealingThemeInline]
    actions = ['retry_failed_plans']

    fieldsets = (
        ('User & Status', {
            'fields': ('user', 'status', 'is_archived', 'generation_error'),
        }),
        ('Lifecycle Timestamps', {
            'fields': ('journey_started_at', 'journey_completed_at', 'created_at', 'updated_at'),
        }),
        ('Assessment Answers', {
            'fields': (
                'q1_emotional_baseline', 'q2_past_influence', 'q3_life_area_impact',
                'q4_core_pain_source', 'q5_coping_pattern', 'q6_relationship_fear',
                'q7_core_belief', 'q8_desired_relief', 'q9_healing_resistance',
                'q10_personal_desire',
            ),
            'classes': ('collapse',),
        }),
        ('AI-Generated Healing Profile', {
            'fields': ('healing_profile_display',),
            'classes': ('collapse',),
        }),
    )

    def healing_profile_display(self, obj):
        """Render the healing profile JSON in a readable format."""
        if obj.healing_profile:
            formatted = json.dumps(obj.healing_profile, indent=2)
            return format_html('<pre style="max-width:600px;overflow-x:auto;">{}</pre>', formatted)
        return "Not generated yet"
    healing_profile_display.short_description = "Healing Profile (JSON)"

    @admin.action(description="Retry failed plan generation")
    def retry_failed_plans(self, request, queryset):
        """Custom action to retry generation for failed assessments."""
        failed = queryset.filter(status='failed')
        count = failed.count()
        if count == 0:
            self.message_user(request, "No failed assessments selected.")
            return

        for assessment in failed:
            assessment.status = 'pending'
            assessment.generation_error = ''
            assessment.save(update_fields=['status', 'generation_error'])
            try:
                from .tasks import generate_healing_plan
                generate_healing_plan.delay(assessment.id)
            except Exception:
                pass  # Celery may not be available in dev

        self.message_user(request, f"Retrying generation for {count} assessment(s).")


# ──────────────────────────────────────────────
# HealingJourneySettings Admin
# ──────────────────────────────────────────────

@admin.register(HealingJourneySettings)
class HealingJourneySettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'timezone', 'morning_reminder_enabled', 'evening_reminder_enabled', 'updated_at')
    list_filter = ('morning_reminder_enabled', 'evening_reminder_enabled')
    search_fields = ('user__email',)


# ──────────────────────────────────────────────
# HealingTheme Admin (read-only)
# ──────────────────────────────────────────────

@admin.register(HealingTheme)
class HealingThemeAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'day_number', 'theme_title', 'theme_category')
    list_filter = ('theme_category',)
    search_fields = ('theme_title', 'assessment__user__email')
    readonly_fields = (
        'assessment', 'day_number', 'theme_title',
        'theme_intention', 'theme_category', 'healing_focus',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# HealingDay Admin
# ──────────────────────────────────────────────

@admin.register(HealingDay)
class HealingDayAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'day_number', 'state', 'content_status',
        'unlock_date', 'completed_at',
    )
    list_filter = ('state', 'content_status')
    search_fields = ('user__email',)
    readonly_fields = (
        'user', 'theme', 'day_number', 'unlock_date',
        'completed_at', 'mood_entry', 'journal_entry',
    )
    inlines = [DayContentInline]


# ──────────────────────────────────────────────
# DayContent Admin (read-only)
# ──────────────────────────────────────────────

@admin.register(DayContent)
class DayContentAdmin(admin.ModelAdmin):
    list_display = ('healing_day', 'is_fallback', 'generated_at')
    list_filter = ('is_fallback',)
    search_fields = ('healing_day__user__email',)
    readonly_fields = (
        'healing_day', 'generated_at', 'is_fallback',
        'guided_reflection', 'affirmation', 'mental_workout',
        'physical_workout', 'breathing_exercise',
        'mini_challenge', 'journal_prompt',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# ──────────────────────────────────────────────
# HealingStreak Admin
# ──────────────────────────────────────────────

@admin.register(HealingStreak)
class HealingStreakAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'current_streak', 'longest_streak',
        'total_days_completed', 'grace_period_active',
        'grace_expires_at', 'updated_at',
    )
    list_filter = ('grace_period_active',)
    search_fields = ('user__email',)
    readonly_fields = (
        'user', 'current_streak', 'longest_streak',
        'last_completed_date', 'total_days_completed',
        'milestones_reached', 'grace_period_active',
        'grace_expires_at', 'updated_at',
    )
