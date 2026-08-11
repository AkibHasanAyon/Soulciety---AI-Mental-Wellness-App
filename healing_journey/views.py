from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
import logging

from .models import HealingAssessment, HealingDay, HealingStreak, HealingJourneySettings
from .serializers import (
    AssessmentSubmissionSerializer,
    AssessmentStatusSerializer,
    HealingProfileSerializer,
    DayDetailSerializer,
    PlanDaySerializer,
    DayCompleteSerializer,
    ProgressSerializer,
    SettingsSerializer,
)

from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

def _sync_user_journey_state(user):
    """
    Synchronise a user's journey state on every API hit.
    Two operations:
      1. Unlock: locked days whose unlock_date <= user's local today → 'available'
      2. Mark missed: available days that were NOT completed AND whose unlock_date
         is strictly BEFORE today → 'missed'  (the day has fully passed)
    This is a failsafe so users don't have to wait for the hourly Celery beat task.
    """
    try:
        settings_obj = user.healing_settings
        user_tz_str = settings_obj.timezone
    except Exception:
        user_tz_str = 'UTC'

    try:
        user_tz = ZoneInfo(user_tz_str)
    except Exception:
        user_tz = ZoneInfo('UTC')

    local_today = timezone.now().astimezone(user_tz).date()

    # 1. Mark missed: available + uncompleted + unlock_date < today
    HealingDay.objects.filter(
        user=user,
        state='available',
        completed_at__isnull=True,
        unlock_date__lt=local_today,
        theme__assessment__is_archived=False,
    ).update(state='missed')

    # 2. Unlock: locked + unlock_date <= today
    HealingDay.objects.filter(
        user=user,
        state='locked',
        unlock_date__lte=local_today,
        theme__assessment__is_archived=False,
    ).update(state='available')

class AssessmentSubmitView(APIView):
    """
    POST /api/healing/assessment/
    Submit the 10-question assessment. Triggers the generate_healing_plan Celery task.

    Re-submission guard logic (Section 2.4):
    - status='ready' (non-archived) → 409 Conflict
    - status='pending' or 'generating' → 202 (keep polling, don't create duplicate task)
    - status='failed' → allow re-submission (overwrite answers, reset to pending)
    - No existing assessment → create new one
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AssessmentSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Extract timezone from header (default to UTC)
        user_timezone = request.headers.get('X-User-Timezone', 'UTC')

        # Check for existing non-archived assessment
        existing = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False
        ).first()

        if existing:
            # Guard: journey already active
            if existing.status == 'ready':
                return Response(
                    {
                        'error': 'active_journey_exists',
                        'message': 'Your journey is already active.',
                    },
                    status=status.HTTP_409_CONFLICT
                )

            # Guard: generation in progress (double-tap race condition)
            if existing.status in ('pending', 'generating'):
                # Stuck-generating recovery: if the assessment has been
                # 'generating' for > 10 min, the worker likely crashed mid-task.
                # Reset to 'failed' so the failed-path below re-triggers it.
                if existing.status == 'generating':
                    age = (timezone.now() - existing.updated_at).total_seconds()
                    if age > 600:  # 10 minutes
                        logger.warning(
                            f"[Assessment] Assessment {existing.id} stuck in 'generating' "
                            f"for {int(age)}s. Resetting to 'failed'."
                        )
                        existing.status = 'failed'
                        existing.generation_error = 'Plan generation timed out (worker restart). Will retry.'
                        existing.save(update_fields=['status', 'generation_error'])
                        # Fall through to the 'failed' handler below
                    else:
                        return Response(
                            {
                                'message': 'Your healing journey is being created...',
                                'assessment_id': existing.id,
                                'status': existing.status,
                            },
                            status=status.HTTP_202_ACCEPTED
                        )
                else:
                    return Response(
                        {
                            'message': 'Your healing journey is being created...',
                            'assessment_id': existing.id,
                            'status': existing.status,
                        },
                        status=status.HTTP_202_ACCEPTED
                    )

            # Allow re-submission after failure:
            # overwrite answers, reset status to 'pending', re-trigger Celery task
            if existing.status == 'failed':
                for field, value in serializer.validated_data.items():
                    setattr(existing, field, value)
                existing.status = 'pending'
                existing.generation_error = ''
                existing.save()

                # Trigger plan generation via Celery (after DB commit)
                def trigger_plan_generation():
                    try:
                        from .tasks import generate_healing_plan
                        generate_healing_plan.delay(existing.id, user_timezone)
                    except Exception as e:
                        logger.warning(f"Failed to queue plan generation for assessment {existing.id}: {e}")

                transaction.on_commit(trigger_plan_generation)

                return Response(
                    {
                        'message': 'Retrying your journey creation...',
                        'assessment_id': existing.id,
                        'status': 'generating',
                    },
                    status=status.HTTP_202_ACCEPTED
                )

        # No existing assessment — create a new one
        assessment = HealingAssessment.objects.create(
            user=request.user,
            **serializer.validated_data,
            status='pending',
        )

        # Trigger plan generation via Celery (after DB commit)
        def trigger_plan_generation():
            try:
                from .tasks import generate_healing_plan
                generate_healing_plan.delay(assessment.id, user_timezone)
            except Exception as e:
                logger.warning(f"Failed to queue plan generation for assessment {assessment.id}: {e}")

        transaction.on_commit(trigger_plan_generation)

        return Response(
            {
                'message': 'Your healing journey is being created...',
                'assessment_id': assessment.id,
                'status': 'generating',
            },
            status=status.HTTP_202_ACCEPTED
        )


class AssessmentQuestionsView(APIView):
    """
    GET /api/healing/assessment/questions/
    Returns the list of onboarding assessment questions and their valid choices.
    This allows the frontend to render the quiz dynamically.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .serializers import (
            Q1_CHOICES, Q3_CHOICES, Q4_CHOICES, Q5_CHOICES,
            Q6_CHOICES, Q7_CHOICES, Q8_CHOICES, Q9_CHOICES
        )

        questions = [
            {
                "id": "q1_emotional_baseline",
                "type": "choice",
                "question": "How would you describe your baseline emotional state lately?",
                "options": Q1_CHOICES
            },
            {
                "id": "q2_past_influence",
                "type": "scale",
                "question": "On a scale of 1-5, how much do you feel past experiences are influencing your present reactions?",
                "min": 1,
                "max": 5
            },
            {
                "id": "q3_life_area_impact",
                "type": "choice",
                "question": "Which area of your life feels the most impacted right now?",
                "options": Q3_CHOICES
            },
            {
                "id": "q4_core_pain_source",
                "type": "choice",
                "question": "When you feel most activated or in pain, what does it usually stem from?",
                "options": Q4_CHOICES
            },
            {
                "id": "q5_coping_pattern",
                "type": "choice",
                "question": "When things get heavy, what is your default coping mechanism?",
                "options": Q5_CHOICES
            },
            {
                "id": "q6_relationship_fear",
                "type": "choice",
                "question": "In relationships, what is your deepest fear?",
                "options": Q6_CHOICES
            },
            {
                "id": "q7_core_belief",
                "type": "choice",
                "question": "If you had to guess, what is the core negative belief you hold about yourself?",
                "options": Q7_CHOICES
            },
            {
                "id": "q8_desired_relief",
                "type": "choice",
                "question": "What are you most tired of carrying?",
                "options": Q8_CHOICES
            },
            {
                "id": "q9_healing_resistance",
                "type": "choice",
                "question": "What has been your biggest block to healing so far?",
                "options": Q9_CHOICES
            },
            {
                "id": "q10_personal_desire",
                "type": "text",
                "question": "If you could change one thing about how you feel every day, what would it be?",
                "placeholder": "Type your answer here..."
            }
        ]

        return Response({"questions": questions})


class AssessmentStatusView(APIView):
    """
    GET /api/healing/assessment/status/
    Poll for plan generation progress. Client polls every 3 seconds
    until status is 'ready' or 'failed'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assessment = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False
        ).first()

        if not assessment:
            return Response(
                {'error': 'No assessment found. Please start your healing journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Stuck-generating recovery: if plan generation has been running
        # for > 10 minutes, the worker likely crashed. Reset to 'failed'
        # so the client sees an error and can retry.
        if assessment.status == 'generating':
            age = (timezone.now() - assessment.updated_at).total_seconds()
            if age > 600:  # 10 minutes
                logger.warning(
                    f"[Status Poll] Assessment {assessment.id} stuck in 'generating' "
                    f"for {int(age)}s. Resetting to 'failed'."
                )
                assessment.status = 'failed'
                assessment.generation_error = 'Plan generation timed out. Please try again.'
                assessment.save(update_fields=['status', 'generation_error'])

        serializer = AssessmentStatusSerializer(assessment)
        return Response(serializer.data)


class AssessmentProfileView(APIView):
    """
    GET /api/healing/assessment/profile/
    Returns the user's healing profile summary and assessment status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        assessment = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False
        ).first()

        if not assessment:
            return Response(
                {'error': 'No assessment found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = HealingProfileSerializer(assessment)
        return Response(serializer.data)


class DayDetailView(APIView):
    """
    GET /api/healing/days/<day_number>/
    Return full day detail with theme + content.

    Behavior:
    - locked → 403 Forbidden
    - day_number out of range [1,30] → 404
    - no journey → 404
    - content not ready (pending/generating) → 202 with polling message
    - content_status='ready' → 200 with full content
    - content_status='failed' + fallback exists → 200 with fallback content

    Content generation is strictly background (Celery tasks).
    No API call triggers content generation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, day_number):
        _sync_user_journey_state(request.user)
        # Validate day_number range
        if day_number < 1 or day_number > 30:
            return Response(
                {'error': f'Day {day_number} does not exist. Valid range: 1–30.'},
                status=status.HTTP_404_NOT_FOUND
            )

        healing_day = HealingDay.objects.select_related(
            'theme', 'theme__assessment'
        ).filter(
            user=request.user,
            day_number=day_number,
            theme__assessment__is_archived=False,
        ).first()

        if not healing_day:
            return Response(
                {'error': 'No healing journey found. Please start your journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Guard: locked days are not accessible
        if healing_day.state == 'locked':
            return Response(
                {
                    'error': 'day_locked',
                    'message': f'Day {day_number} is locked. It unlocks on {healing_day.unlock_date}.',
                    'unlock_date': str(healing_day.unlock_date),
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Content not ready yet — tell the client to poll later
        # Content generation is handled strictly by background Celery tasks
        if healing_day.content_status in ('pending', 'generating'):
            return Response(
                {
                    'message': "Your day's content is being prepared...",
                    'day_number': day_number,
                    'content_status': healing_day.content_status,
                    'state': healing_day.state,
                },
                status=status.HTTP_202_ACCEPTED
            )

        # Content failed but fallback exists — serve it
        if healing_day.content_status == 'failed':
            if hasattr(healing_day, 'content'):
                serializer = DayDetailSerializer(healing_day)
                return Response(serializer.data)
            # No fallback yet — report as pending
            return Response(
                {
                    'message': "Your day's content is being prepared...",
                    'day_number': day_number,
                    'content_status': healing_day.content_status,
                    'state': healing_day.state,
                },
                status=status.HTTP_202_ACCEPTED
            )

        # Content is ready — return full detail
        serializer = DayDetailSerializer(healing_day)
        return Response(serializer.data)


class TodayView(APIView):
    """
    GET /api/healing/today/
    Returns the current available day's data. Always returns a meaningful state.

    States:
    - no_plan: user hasn't started their journey
    - generating: plan is being generated
    - journey_complete: all 30 days done
    - available day: returns full day detail (delegates to DayDetailSerializer)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _sync_user_journey_state(request.user)
        # Check for active assessment
        assessment = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False
        ).first()

        if not assessment:
            return Response({
                'state': 'no_plan',
                'message': "You haven't started your healing journey yet.",
            })

        if assessment.status in ('pending', 'generating'):
            return Response({
                'state': 'generating',
                'message': 'Your healing journey is still being prepared...',
            })

        if assessment.status == 'failed':
            return Response({
                'state': 'failed',
                'message': 'Something went wrong creating your journey. Please try again.',
            })

        # Journey is ready — check for completion
        if assessment.journey_completed_at:
            return Response({
                'state': 'journey_complete',
                'message': "You've completed your 30-day journey. Well done.",
                'journey_completed_at': assessment.journey_completed_at,
            })

        today_day = HealingDay.objects.select_related(
            'theme', 'theme__assessment'
        ).filter(
            user=request.user,
            state='available',
            completed_at__isnull=True,
            theme__assessment__is_archived=False,
        ).order_by('day_number').first()

        if not today_day:
            # All available days are completed, but journey not marked complete yet
            # Return the most recent completed day
            last_completed = HealingDay.objects.select_related(
                'theme'
            ).filter(
                user=request.user,
                state='completed',
                theme__assessment__is_archived=False,
            ).order_by('-day_number').first()

            if last_completed:
                serializer = DayDetailSerializer(last_completed)
                return Response(serializer.data)

            return Response({
                'state': 'no_plan',
                'message': "You haven't started your healing journey yet.",
            })

        serializer = DayDetailSerializer(today_day)
        return Response(serializer.data)


class PlanOverviewView(APIView):
    """
    GET /api/healing/plan/
    Returns the full 30-day plan with per-day state for the grid UI.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _sync_user_journey_state(request.user)
        assessment = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False
        ).first()

        if not assessment:
            return Response(
                {'error': 'No healing plan found. Please start your journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        if assessment.status != 'ready':
            return Response(
                {'error': 'Your healing plan is not ready yet.', 'status': assessment.status},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get all days with themes
        days = HealingDay.objects.select_related(
            'theme'
        ).filter(
            user=request.user,
            theme__assessment__is_archived=False,
        ).order_by('day_number')

        healing_profile = assessment.healing_profile or {}
        healing_arc_summary = healing_profile.get('healing_arc_summary', '')

        serializer = PlanDaySerializer(days, many=True)

        return Response({
            'healing_arc_summary': healing_arc_summary,
            'themes': serializer.data,
        })


# Milestone definitions (Section 6.3)
MILESTONE_MESSAGES = {
    3: "3-day streak! You're building something real.",
    7: 'One full week. Your nervous system is changing.',
    14: 'Halfway there. You should be proud.',
    21: '21 days. This is who you are now.',
    30: 'You did it. 30 days of choosing yourself.',
}


class DayCompleteView(APIView):
    """
    POST /api/healing/days/<day_number>/complete/
    Mark a day as completed. Idempotent.

    Accepts optional mood + journal_entry_id.
    Handles streak update, grace period recovery, milestone detection,
    and journey completion (Day 30).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, day_number):
        # Validate day range
        if day_number < 1 or day_number > 30:
            return Response(
                {'error': f'Day {day_number} does not exist.'},
                status=status.HTTP_404_NOT_FOUND
            )

        with transaction.atomic():
            healing_day = HealingDay.objects.select_for_update().select_related('theme').filter(
                user=request.user,
                day_number=day_number,
                theme__assessment__is_archived=False,
            ).first()

            if not healing_day:
                return Response(
                    {'error': 'No healing journey found.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Guard: locked days cannot be completed
            if healing_day.state == 'locked':
                return Response(
                    {'error': 'day_locked', 'message': f'Day {day_number} is locked.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Idempotency guard: already completed
            if healing_day.state == 'completed':
                streak = HealingStreak.objects.filter(user=request.user).first()
                return Response({
                    'message': f'Day {day_number} was already completed.',
                    'current_streak': streak.current_streak if streak else 0,
                    'already_completed': True,
                })

            # Validate optional input
            serializer = DayCompleteSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            mood_value = serializer.validated_data.get('mood')
            journal_entry_id = serializer.validated_data.get('journal_entry_id')

            now = timezone.now()

            # Complete the day
            healing_day.state = 'completed'
            healing_day.completed_at = now

            # Create mood entry if provided
            if mood_value:
                try:
                    from app_home.models import MoodEntry
                    mood_entry = MoodEntry.objects.create(
                        user=request.user,
                        mood=mood_value,
                        note=f'Healing Journey Day {day_number}',
                    )
                    healing_day.mood_entry = mood_entry
                except Exception as e:
                    logger.warning(f"[Complete] Failed to create mood entry: {e}")

            # Link journal entry if provided
            if journal_entry_id:
                try:
                    from journal.models import JournalEntry
                    journal_entry = JournalEntry.objects.get(
                        id=journal_entry_id, user=request.user
                    )
                    healing_day.journal_entry = journal_entry
                except Exception as e:
                    logger.warning(f"[Complete] Failed to link journal entry: {e}")

            healing_day.save()

            # Update streak utilizing a database lock
            streak, _ = HealingStreak.objects.select_for_update().get_or_create(
                user=request.user,
                defaults={
                    'current_streak': 0,
                    'longest_streak': 0,
                    'total_days_completed': 0,
                    'milestones_reached': [],
                }
            )

            streak.current_streak += 1
            streak.total_days_completed += 1
            streak.last_completed_date = now.date()

            # Update longest streak
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak

            # Grace period recovery: if user completes a missed day during grace
            if streak.grace_period_active:
                streak.grace_period_active = False
                streak.grace_expires_at = None

            streak.save()

            # Milestone detection
            milestone_reached = None
            milestone_day = streak.total_days_completed
            if milestone_day in MILESTONE_MESSAGES:
                if milestone_day not in (streak.milestones_reached or []):
                    milestone_reached = {
                        'day': milestone_day,
                        'message': MILESTONE_MESSAGES[milestone_day],
                    }
                    milestones = list(streak.milestones_reached or [])
                    milestones.append(milestone_day)
                    streak.milestones_reached = milestones
                    streak.save(update_fields=['milestones_reached'])

                    # Send milestone notification
                    try:
                        from notifications.helpers import create_notification
                        create_notification(
                            user=request.user,
                            title=f'\U0001f31f Milestone: Day {milestone_day}!',
                            message=MILESTONE_MESSAGES[milestone_day],
                            notif_type='healing_milestone',
                            data={'type': 'healing_milestone', 'day': milestone_day},
                        )
                    except Exception as e:
                        logger.warning(f"[Complete] Failed to send milestone notification: {e}")

            # Journey completion (Day 30)
            if day_number == 30:
                assessment = HealingAssessment.objects.filter(
                    user=request.user, is_archived=False
                ).first()
                if assessment and not assessment.journey_completed_at:
                    assessment.journey_completed_at = now
                    assessment.save(update_fields=['journey_completed_at'])

                    try:
                        from notifications.helpers import create_notification
                        create_notification(
                            user=request.user,
                            title='\U0001f33f Journey Complete!',
                            message="You've completed your 30-Day Healing Journey. You should be incredibly proud.",
                            notif_type='healing_complete',
                            data={'type': 'healing_journey_complete'},
                        )
                    except Exception as e:
                        logger.warning(f"[Complete] Failed to send completion notification: {e}")

            return Response({
                'message': f'Day {day_number} complete.',
                'current_streak': streak.current_streak,
                'total_days_completed': streak.total_days_completed,
                'milestone_reached': milestone_reached,
            })


class ProgressView(APIView):
    """
    GET /api/healing/progress/
    Returns streak data, milestones, and grace status.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        streak = HealingStreak.objects.filter(user=request.user).first()

        if not streak:
            return Response(
                {'error': 'No progress data found. Please start your journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProgressSerializer(streak)
        return Response(serializer.data)


class SettingsView(APIView):
    """
    GET /api/healing/settings/   — Return reminder preferences.
    PATCH /api/healing/settings/ — Update preferences + timezone.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            settings_obj = HealingJourneySettings.objects.get(user=request.user)
        except HealingJourneySettings.DoesNotExist:
            return Response(
                {'error': 'No healing settings found. Please start your journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SettingsSerializer(settings_obj)
        return Response(serializer.data)

    def patch(self, request):
        try:
            settings_obj = HealingJourneySettings.objects.get(user=request.user)
        except HealingJourneySettings.DoesNotExist:
            return Response(
                {'error': 'No healing settings found. Please start your journey first.'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SettingsSerializer(settings_obj, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data)


class ResetJourneyView(APIView):
    """
    POST /api/healing/reset/
    Archive the current journey and allow starting a new one.

    Steps:
        1. Soft-archive the current HealingAssessment (is_archived=True).
        2. Reset HealingStreak to defaults (zero counters, clear grace).
        3. HealingJourneySettings are preserved (timezone + reminder prefs carry over).
        4. User is returned to the onboarding flow.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Find active (non-archived) assessment
        assessment = HealingAssessment.objects.filter(
            user=request.user,
            is_archived=False,
        ).first()

        if not assessment:
            return Response(
                {'error': 'no_active_journey', 'message': 'No active journey to reset.'},
                status=status.HTTP_404_NOT_FOUND
            )

        archived_id = assessment.id

        with transaction.atomic():
            # Step 1: Soft-archive the assessment
            assessment.is_archived = True
            assessment.save(update_fields=['is_archived'])

            # Step 2: Reset streak to defaults
            try:
                streak = HealingStreak.objects.get(user=request.user)
                streak.current_streak = 0
                streak.longest_streak = 0
                streak.total_days_completed = 0
                streak.last_completed_date = None
                streak.milestones_reached = []
                streak.grace_period_active = False
                streak.grace_expires_at = None
                streak.save()
            except HealingStreak.DoesNotExist:
                pass

            # Step 3: Settings are preserved — timezone and reminder prefs carry forward

        return Response({
            'message': "Your previous journey has been archived. Start your new journey when you're ready.",
            'archived_journey_id': archived_id,
        })


# ──────────────────────────────────────────────
# Phase 9: Saved Affirmations & Community Sharing
# ──────────────────────────────────────────────

from .models import SavedAffirmation
from .serializers import SavedAffirmationSerializer, ShareToCommunitySerializer
from django.db import IntegrityError

class SavedAffirmationListView(APIView):
    """
    GET /api/healing/affirmations/
    List all saved affirmations for the user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        affirmations = SavedAffirmation.objects.filter(user=request.user)
        serializer = SavedAffirmationSerializer(affirmations, many=True)
        return Response(serializer.data)


class DeleteSavedAffirmationView(APIView):
    """
    DELETE /api/healing/affirmations/<pk>/
    Unsave an affirmation.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        try:
            affirmation = SavedAffirmation.objects.get(pk=pk, user=request.user)
            affirmation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except SavedAffirmation.DoesNotExist:
            return Response({'error': 'Affirmation not found.'}, status=status.HTTP_404_NOT_FOUND)


class SaveDayAffirmationView(APIView):
    """
    POST /api/healing/days/<day_number>/save-affirmation/
    Save the affirmation from a specific day's content.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, day_number):
        healing_day = HealingDay.objects.filter(
            user=request.user,
            day_number=day_number,
            theme__assessment__is_archived=False,
        ).first()

        if not healing_day or not hasattr(healing_day, 'content'):
            return Response({'error': 'Content not found for this day.'}, status=status.HTTP_404_NOT_FOUND)

        text = healing_day.content.affirmation

        try:
            SavedAffirmation.objects.create(
                user=request.user,
                text=text,
                day_number=day_number
            )
            return Response({'message': 'Affirmation saved successfully.'}, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({'message': 'Affirmation already saved.'}, status=status.HTTP_200_OK)


class ShareToCommunityView(APIView):
    """
    POST /api/healing/days/<day_number>/share/
    Share the day's affirmation or journal entry to the community feed.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, day_number):
        serializer = ShareToCommunitySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        share_type = serializer.validated_data['type']

        healing_day = HealingDay.objects.select_related('journal_entry').filter(
            user=request.user,
            day_number=day_number,
            theme__assessment__is_archived=False,
        ).first()

        if not healing_day:
            return Response({'error': 'Healing day not found.'}, status=status.HTTP_404_NOT_FOUND)

        content_text = ""

        if share_type == 'affirmation':
            if not hasattr(healing_day, 'content'):
                return Response({'error': 'Affirmation not found for this day.'}, status=status.HTTP_404_NOT_FOUND)
            content_text = healing_day.content.affirmation
        elif share_type == 'journal':
            if not healing_day.journal_entry:
                return Response({'error': 'Journal entry not linked to this day.'}, status=status.HTTP_404_NOT_FOUND)
            content_text = healing_day.journal_entry.content

        # Create Community Post (raw text, from user profile)
        try:
            from community.models import CommunityPost
            CommunityPost.objects.create(
                user=request.user,
                content=content_text
            )
            return Response({'message': 'Shared to community successfully.'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Failed to share to community: {e}")
            return Response({'error': 'Failed to share.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class HealingReflectionView(APIView):
    """
    POST /api/healing/days/<day_number>/reflection/
    Save the user's reflection from the mental exercise.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, day_number):
        healing_day = HealingDay.objects.filter(
            user=request.user,
            day_number=day_number,
            theme__assessment__is_archived=False,
        ).first()

        if not healing_day:
            return Response({'error': 'Healing day not found.'}, status=status.HTTP_404_NOT_FOUND)

        reflection_text = request.data.get('mentalreflectiontext')
        if not reflection_text or not str(reflection_text).strip():
            return Response({'error': 'mentalreflectiontext is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from .models import HealingReflection
        reflection = HealingReflection.objects.create(
            user=request.user,
            healing_day=healing_day,
            reflection_text=reflection_text.strip()
        )

        # Trigger background task to extract memory
        from .tasks import extract_healing_reflection_memories
        extract_healing_reflection_memories.delay(reflection.id)

        from .serializers import HealingReflectionSerializer
        return Response(HealingReflectionSerializer(reflection).data, status=status.HTTP_201_CREATED)
