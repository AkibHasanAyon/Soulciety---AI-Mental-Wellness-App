# healing_journey/tasks.py
"""
Celery background tasks for the 30-Day Healing Journey.
"""
import json
import re
import logging
from datetime import timedelta

from celery import shared_task
from celery.exceptions import Retry
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from google import genai
from google.genai import types

from .models import (
    HealingAssessment,
    HealingJourneySettings,
    HealingTheme,
    HealingDay,
    DayContent,
    HealingStreak,
)
from .prompts import (
    PLAN_GENERATION_SYSTEM_PROMPT,
    CONTENT_GENERATION_SYSTEM_PROMPT,
    build_plan_generation_prompt,
    build_content_generation_prompt,
)
from .validators import (
    validate_plan_response,
    validate_day_content,
    PlanValidationError,
    ContentValidationError,
)

logger = logging.getLogger(__name__)

# Lazy-init Gemini client (reused across task invocations in the same worker)
_gemini_client = None


def _get_gemini_client():
    """Get or create a reusable Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(
            api_key=settings.GEMINI_API_KEY,
            http_options={'timeout': 600000}
        )
    return _gemini_client


def _parse_json_response(raw_text):
    """
    Parse JSON from Gemini's response, stripping markdown fences if present.

    Args:
        raw_text: str — raw response text from Gemini

    Returns:
        dict — parsed JSON data

    Raises:
        json.JSONDecodeError: if the text is not valid JSON
    """
    cleaned = raw_text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        cleaned = re.sub(r'\s*```\s*$', '', cleaned)
    return json.loads(cleaned)


# ──────────────────────────────────────────────
# Task 9.1: generate_healing_plan
# ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=4, default_retry_delay=60)
def generate_healing_plan(self, assessment_id, user_timezone='UTC'):
    """
    Generate the full 30-day healing plan for a user.

    Triggered via transaction.on_commit() after assessment submission.
    Steps:
        1. Set status → 'generating'
        2. Build Gemini prompt from assessment answers
        3. Call Gemini API
        4. Parse + validate JSON response
        5. Save healing profile
        6. Atomically create 30 themes + 30 days + streak + settings
        7. Set status → 'ready'
        8. Trigger Day 1 content generation
        9. Send notifications

    On failure (after 3 retries):
        - Set status → 'failed'
        - Store error in generation_error
        - Send failure notification
    """
    try:
        assessment = HealingAssessment.objects.get(id=assessment_id)
    except HealingAssessment.DoesNotExist:
        logger.error(f"Assessment {assessment_id} not found. Task aborted.")
        return f"Assessment {assessment_id} not found"

    # Guard: prevent duplicate generation on retries or concurrent submissions
    if assessment.status == 'ready' or HealingTheme.objects.filter(assessment=assessment).exists():
        logger.info(f"[Plan Gen] Plan already generated for assessment {assessment_id}. Skipping.")
        if assessment.status != 'ready':
            assessment.status = 'ready'
            assessment.save(update_fields=['status'])
        return f"Plan already generated for assessment {assessment_id}"

    try:
        # Step 1: Set status → 'generating'
        assessment.status = 'generating'
        assessment.save(update_fields=['status'])
        logger.info(f"[Plan Gen] Starting for assessment {assessment_id} (user: {assessment.user})")

        # Step 2: Build prompt
        user_prompt = build_plan_generation_prompt(assessment)

        # Step 3 & 4: Call Gemini API and parse
        healing_profile = None
        themes_data = None
        
        try:
            model_name = 'gemini-3.5-flash' # Using flash instead of pro due to 503s and hangs
            if self.request.retries >= 3:
                logger.info(f"[Plan Gen] Using {model_name} for attempt {self.request.retries + 1}")

            client = _get_gemini_client()
            response = client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(
                    system_instruction=PLAN_GENERATION_SYSTEM_PROMPT,
                    temperature=0.8,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                ),
                contents=[{
                    'role': 'user',
                    'parts': [{'text': user_prompt}],
                }],
            )

            if not response or not response.text:
                raise Exception("Empty response from Gemini API")

            raw_text = response.text
            logger.debug(f"[Plan Gen] Raw response length: {len(raw_text)} chars")

            parsed_data = _parse_json_response(raw_text)
            healing_profile, themes_data = validate_plan_response(parsed_data)
            generation_error_msg = ''
            
        except (PlanValidationError, json.JSONDecodeError, Exception) as exc:
            if self.request.retries < self.max_retries:
                logger.warning(
                    f"[Plan Gen] Generation error for assessment {assessment_id}: {exc}. "
                    f"Retry {self.request.retries + 1}/{self.max_retries}"
                )
                raise self.retry(exc=exc)
            
            # Exhausted all API retries. Use offline fallback.
            logger.error(f"[Plan Gen] All API attempts failed. Falling back to offline plan for assessment {assessment_id}")
            from .fallbacks import get_fallback_healing_plan
            healing_profile, themes_data = get_fallback_healing_plan()
            generation_error_msg = f"Used offline fallback. Final API Error: {str(exc)}"[:2000]

        # Step 5 & 6: Save healing profile and create all records atomically
        now = timezone.now()
        
        try:
            from zoneinfo import ZoneInfo
            user_tz = ZoneInfo(user_timezone)
        except Exception:
            user_tz = ZoneInfo('UTC')
            
        local_now = now.astimezone(user_tz)
        local_today = local_now.date()
        
        from datetime import timedelta
        # If user joins at or after 6 PM local time, Day 1 officially starts tomorrow
        # (giving them more than 6 hours for their first day)
        if local_now.hour >= 18:
            journey_start_date = local_today + timedelta(days=1)
        else:
            journey_start_date = local_today

        with transaction.atomic():
            # Save healing profile + set journey started
            assessment.healing_profile = healing_profile
            assessment.journey_started_at = now
            assessment.status = 'ready'
            assessment.generation_error = generation_error_msg
            assessment.save(update_fields=[
                'healing_profile', 'journey_started_at', 'status', 'generation_error'
            ])

            # Create 30 HealingTheme records
            theme_objects = []
            for theme_data in sorted(themes_data, key=lambda t: t['day_number']):
                theme_objects.append(HealingTheme(
                    assessment=assessment,
                    day_number=theme_data['day_number'],
                    theme_title=theme_data['theme_title'],
                    theme_intention=theme_data['theme_intention'],
                    theme_category=theme_data['theme_category'],
                    healing_focus=theme_data['healing_focus'],
                ))
            created_themes = HealingTheme.objects.bulk_create(theme_objects)

            # Create 30 HealingDay records with pre-calculated unlock dates
            day_objects = []
            for theme in created_themes:
                unlock_offset = timedelta(days=theme.day_number - 1)
                day_unlock = journey_start_date + unlock_offset
                # Day 1 is available immediately only if journey starts today.
                # If journey starts tomorrow (user joined after 6 PM), Day 1
                # stays locked — the hourly unlock task will open it at midnight.
                if theme.day_number == 1 and journey_start_date == local_today:
                    initial_state = 'available'
                else:
                    initial_state = 'locked'
                day_objects.append(HealingDay(
                    user=assessment.user,
                    theme=theme,
                    day_number=theme.day_number,
                    unlock_date=day_unlock,
                    state=initial_state,
                    content_status='pending',
                ))
            HealingDay.objects.bulk_create(day_objects)

            # Create HealingStreak (all zeros)
            HealingStreak.objects.get_or_create(
                user=assessment.user,
                defaults={
                    'current_streak': 0,
                    'longest_streak': 0,
                    'total_days_completed': 0,
                    'milestones_reached': [],
                    'grace_period_active': False,
                }
            )

            # Create HealingJourneySettings
            HealingJourneySettings.objects.get_or_create(
                user=assessment.user,
                defaults={
                    'timezone': user_timezone,
                }
            )

        logger.info(
            f"[Plan Gen] SUCCESS for assessment {assessment_id}. "
            f"Created 30 themes + 30 days. Journey starts {journey_start_date}"
        )

        # Step 8: Trigger Day 1 content generation
        day_1 = HealingDay.objects.filter(
            theme__assessment=assessment, day_number=1
        ).first()
        if day_1:
            try:
                generate_day_content.delay(day_1.id)
                logger.info(f"[Plan Gen] Triggered Day 1 content generation (day_id={day_1.id})")
            except Exception as e:
                logger.warning(f"[Plan Gen] Failed to queue Day 1 content: {e}")

        # Step 9: Send notifications
        try:
            from notifications.helpers import create_notification
            create_notification(
                user=assessment.user,
                title='🌿 Your Journey Awaits',
                message='Your 30-Day Healing Journey is ready. Day 1 awaits.',
                notif_type='system',
                data={'type': 'healing_plan_ready', 'assessment_id': str(assessment.id)},
            )
        except Exception as notif_err:
            logger.warning(f"[Plan Gen] Failed to send notification: {notif_err}")

        return f"Plan generated for assessment {assessment_id}"

    except Retry:
        raise
    except Exception as exc:
        logger.error(
            f"[Plan Gen] Unexpected database/system error for assessment {assessment_id}: {exc}",
            exc_info=True
        )
        if self.request.retries >= self.max_retries:
            _mark_plan_failed(assessment, str(exc))
            return f"Plan generation failed for assessment {assessment_id}: {exc}"
        raise self.retry(exc=exc)


def _mark_plan_failed(assessment, error_message):
    """Mark a plan as failed and notify the user."""
    assessment.status = 'failed'
    assessment.generation_error = error_message[:2000]  # Truncate long errors
    assessment.save(update_fields=['status', 'generation_error'])
    logger.error(f"[Plan Gen] FAILED permanently for assessment {assessment.id}: {error_message}")

    try:
        from notifications.helpers import create_notification
        create_notification(
            user=assessment.user,
            title='Something went wrong',
            message='Something went wrong creating your journey. Please try again.',
            notif_type='system',
            data={'type': 'healing_plan_failed', 'assessment_id': str(assessment.id)},
        )
    except Exception as notif_err:
        logger.warning(f"[Plan Gen] Failed to send failure notification: {notif_err}")


# ──────────────────────────────────────────────
# Task 9.2: generate_day_content
# ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def generate_day_content(self, healing_day_id):
    """
    Generate all 7 content modules for a single HealingDay.

    Triggers:
        - After generate_healing_plan for Day 1 (immediate)
        - From generate_day_content_batch (Celery Beat, hourly)

    Steps:
        1. Set content_status → 'generating'
        2. Build prompt from theme + healing profile
        3. Call Gemini API
        4. Parse + validate JSON (7 modules + breathing exercise)
        5. Create DayContent record
        6. Set content_status → 'ready'

    On failure (after 3 retries):
        - Set content_status → 'failed'
        - Trigger serve_fallback_content
    """
    try:
        healing_day = HealingDay.objects.select_related(
            'theme', 'theme__assessment'
        ).get(id=healing_day_id)
    except HealingDay.DoesNotExist:
        logger.error(f"HealingDay {healing_day_id} not found. Task aborted.")
        return f"HealingDay {healing_day_id} not found"

    # Guard: skip if content already exists (avoids double-writes on retries)
    if DayContent.objects.filter(healing_day_id=healing_day_id).exists():
        logger.info(f"[Content Gen] Day {healing_day.day_number} already has content. Skipping.")
        healing_day.content_status = 'ready'
        healing_day.save(update_fields=['content_status'])
        return f"Content already exists for day {healing_day_id}"

    try:
        # Step 1: Set status
        healing_day.content_status = 'generating'
        healing_day.save(update_fields=['content_status'])
        logger.info(f"[Content Gen] Starting for Day {healing_day.day_number} (day_id={healing_day_id})")

        # Step 2: Build prompt
        user_prompt = build_content_generation_prompt(healing_day)

        # Step 3: Call Gemini API
        model_name = 'gemini-3.5-flash'
        if self.request.retries >= 2:
            logger.info(f"[Content Gen] Retry {self.request.retries + 1} with {model_name}")

        client = _get_gemini_client()
        response = client.models.generate_content(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=CONTENT_GENERATION_SYSTEM_PROMPT,
                temperature=0.9,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
            contents=[{
                'role': 'user',
                'parts': [{'text': user_prompt}],
            }],
        )

        if not response or not response.text:
            raise Exception("Empty response from Gemini API")

        # Step 4: Parse + validate
        raw_text = response.text
        parsed_data = _parse_json_response(raw_text)
        validated_content = validate_day_content(parsed_data)

        # Step 5: Create DayContent record
        DayContent.objects.create(
            healing_day=healing_day,
            guided_reflection=validated_content['guided_reflection'],
            affirmation=validated_content['affirmation'],
            mental_workout=validated_content['mental_workout'],
            physical_workout=validated_content['physical_workout'],
            breathing_exercise=validated_content['breathing_exercise'],
            mini_challenge=validated_content['mini_challenge'],
            journal_prompt=validated_content['journal_prompt'],
            is_fallback=False,
        )

        # Step 6: Set content_status → 'ready'
        healing_day.content_status = 'ready'
        healing_day.save(update_fields=['content_status'])

        logger.info(f"[Content Gen] SUCCESS for Day {healing_day.day_number} (day_id={healing_day_id})")
        return f"Content generated for day {healing_day_id}"

    except (ContentValidationError, json.JSONDecodeError) as validation_err:
        logger.warning(
            f"[Content Gen] Validation error for Day {healing_day.day_number}: {validation_err}. "
            f"Retry {self.request.retries + 1}/{self.max_retries}"
        )
        if self.request.retries >= self.max_retries:
            _handle_content_failure(healing_day)
            return f"Content generation failed for day {healing_day_id}: {validation_err}"
        raise self.retry(exc=validation_err)

    except Exception as exc:
        logger.error(
            f"[Content Gen] Error for Day {healing_day.day_number}: {exc}",
            exc_info=True
        )
        if self.request.retries >= self.max_retries:
            _handle_content_failure(healing_day)
            return f"Content generation failed for day {healing_day_id}: {exc}"
        raise self.retry(exc=exc)


def _handle_content_failure(healing_day):
    """Mark content as failed and trigger fallback."""
    healing_day.content_status = 'failed'
    healing_day.save(update_fields=['content_status'])
    logger.error(f"[Content Gen] FAILED permanently for Day {healing_day.day_number}")

    try:
        serve_fallback_content.delay(healing_day.id)
    except Exception as e:
        logger.warning(f"[Content Gen] Failed to queue fallback for Day {healing_day.day_number}: {e}")


# ──────────────────────────────────────────────
# Task 9.7: serve_fallback_content
# ──────────────────────────────────────────────

@shared_task
def serve_fallback_content(healing_day_id):
    """
    Serve fallback content for a day when AI generation has failed.

    Steps:
        1. Select fallback content by theme_category
        2. Create DayContent with is_fallback=True
        3. Set content_status → 'ready'
        4. Log the fallback event
    """
    from .fallbacks import get_fallback_content

    try:
        healing_day = HealingDay.objects.select_related('theme').get(id=healing_day_id)
    except HealingDay.DoesNotExist:
        logger.error(f"[Fallback] HealingDay {healing_day_id} not found.")
        return f"HealingDay {healing_day_id} not found"

    # Guard: don't overwrite existing content
    if DayContent.objects.filter(healing_day_id=healing_day_id).exists():
        logger.info(f"[Fallback] Day {healing_day.day_number} already has content. Skipping.")
        return f"Content already exists for day {healing_day_id}"

    theme_category = healing_day.theme.theme_category

    try:
        fallback_data = get_fallback_content(theme_category)
    except KeyError as e:
        logger.error(f"[Fallback] {e}")
        return str(e)

    DayContent.objects.create(
        healing_day=healing_day,
        guided_reflection=fallback_data['guided_reflection'],
        affirmation=fallback_data['affirmation'],
        mental_workout=fallback_data['mental_workout'],
        physical_workout=fallback_data['physical_workout'],
        breathing_exercise=fallback_data['breathing_exercise'],
        mini_challenge=fallback_data['mini_challenge'],
        journal_prompt=fallback_data['journal_prompt'],
        is_fallback=True,
    )

    healing_day.content_status = 'ready'
    healing_day.save(update_fields=['content_status'])

    logger.warning(
        f"[Fallback] Served fallback content for Day {healing_day.day_number} "
        f"(category={theme_category}, day_id={healing_day_id})"
    )
    return f"Fallback content served for day {healing_day_id}"


# ──────────────────────────────────────────────
# Task 9.3: generate_day_content_batch
# ──────────────────────────────────────────────

@shared_task
def generate_day_content_batch():
    """
    Pre-generate content for upcoming days, 6 hours prior to their midnight.
    Triggered by Celery Beat hourly (0 * * * *).

    Three passes:
      0. Stuck-state recovery: reset days where content_status='generating'
         but no DayContent record exists (worker crashed / container restarted).
         Resets them to 'pending' so they are picked up this tick.
      1. If user's local time >= 18:00, generate tomorrow's pending content.
      2. Safety net: generate any pending content whose unlock_date <= today
         (covers newly-unlocked days and stuck-recovery resets).
    """
    from zoneinfo import ZoneInfo
    from datetime import timedelta

    now_utc = timezone.now()

    # ── Pass 0: Reset stuck-generating days ─────────────────────────────────
    # A day is "stuck" when content_status='generating' but DayContent was
    # never written (e.g. the worker restarted mid-task). Since there is no
    # 'generating_since' field, we always reset — the guard inside
    # generate_day_content (skip if content already exists) prevents doubles.
    stuck_day_ids = []
    generating_day_ids = list(
        HealingDay.objects.filter(
            content_status='generating',
            theme__assessment__is_archived=False,
        ).values_list('id', flat=True)
    )
    # Find which of these actually have a DayContent record
    has_content_ids = set(
        DayContent.objects.filter(
            healing_day_id__in=generating_day_ids
        ).values_list('healing_day_id', flat=True)
    )
    stuck_day_ids = [did for did in generating_day_ids if did not in has_content_ids]

    if stuck_day_ids:
        HealingDay.objects.filter(id__in=stuck_day_ids).update(content_status='pending')
        logger.warning(
            f"[Batch] Reset {len(stuck_day_ids)} stuck-generating days → pending: {stuck_day_ids}"
        )

    # ── Pass 1 & 2: Generate pending content ────────────────────────────────
    pending_days = HealingDay.objects.filter(
        content_status='pending',
        theme__assessment__is_archived=False,
    ).select_related('user', 'user__healing_settings')

    user_tz_cache = {}
    count = 0

    for healing_day in pending_days:
        user_id = healing_day.user_id

        if user_id not in user_tz_cache:
            try:
                settings_obj = healing_day.user.healing_settings
                user_tz_cache[user_id] = settings_obj.timezone
            except Exception:
                user_tz_cache[user_id] = 'UTC'

        try:
            user_tz = ZoneInfo(user_tz_cache[user_id])
        except Exception:
            user_tz = ZoneInfo('UTC')

        local_now = now_utc.astimezone(user_tz)
        local_today = local_now.date()
        tomorrow_local = local_today + timedelta(days=1)

        should_generate = False

        # Pass 1: It's 6 PM or later → pre-generate tomorrow's content
        if local_now.hour >= 18 and healing_day.unlock_date == tomorrow_local:
            should_generate = True

        # Pass 2: Safety net — today's or any past day still has no content.
        # unlock_date <= local_today covers: today's newly-unlocked days AND
        # any missed/stuck days reset in Pass 0.
        if healing_day.unlock_date <= local_today:
            should_generate = True

        if should_generate:
            healing_day.content_status = 'generating'
            healing_day.save(update_fields=['content_status'])

            try:
                delay_seconds = count * 5  # stagger: 5 seconds apart
                generate_day_content.apply_async(args=[healing_day.id], countdown=delay_seconds)
                count += 1
            except Exception as e:
                healing_day.content_status = 'pending'
                healing_day.save(update_fields=['content_status'])
                logger.warning(f"[Batch] Failed to queue content for day {healing_day.id}: {e}")

    logger.info(f"[Batch] Dispatched {count} content generation tasks")
    return f"Dispatched {count} tasks"


# ──────────────────────────────────────────────
# Task 9.4: unlock_healing_days
# ──────────────────────────────────────────────

@shared_task
def unlock_healing_days():
    """
    Transition locked days to available based on user's local timezone.

    Triggered by Celery Beat hourly (0 * * * *).
    For each locked day, converts current UTC time to the user's local time.
    If the user's local date >= the day's unlock_date, transitions to 'available'.

    Why hourly? Users are spread across all timezones. Running hourly ensures
    each user's day unlocks within ~1 hour of their local midnight.
    """
    from zoneinfo import ZoneInfo

    now_utc = timezone.now()

    # Fetch all locked days with their user's settings in one query
    locked_days = HealingDay.objects.filter(
        state='locked',
        theme__assessment__is_archived=False,
    ).select_related('user', 'user__healing_settings')

    # Cache user timezone lookups to avoid repeated queries
    user_tz_cache = {}
    unlocked_count = 0

    for healing_day in locked_days:
        user_id = healing_day.user_id

        if user_id not in user_tz_cache:
            try:
                settings_obj = healing_day.user.healing_settings
                user_tz_cache[user_id] = settings_obj.timezone
            except Exception:
                user_tz_cache[user_id] = 'UTC'

        try:
            user_tz = ZoneInfo(user_tz_cache[user_id])
        except Exception:
            user_tz = ZoneInfo('UTC')

        local_now = now_utc.astimezone(user_tz)
        local_today = local_now.date()

        if healing_day.unlock_date <= local_today:
            healing_day.state = 'available'
            healing_day.save(update_fields=['state'])
            unlocked_count += 1

    logger.info(f"[Unlock] Unlocked {unlocked_count} healing days")
    return f"Unlocked {unlocked_count} days"


# ──────────────────────────────────────────────
# Task 9.5: check_missed_days_and_streaks
# ──────────────────────────────────────────────

@shared_task
def check_missed_days_and_streaks():
    """
    Mark missed days and handle grace period logic.

    Triggered by Celery Beat hourly (0 * * * *).
    Runs hourly because users span all timezones — a fixed UTC run would mark
    East Coast users' days as missed while they still have hours left.

    Steps:
        1. Find days where state='available' and completed_at is NULL.
        2. For each, check if user's local date > unlock_date (day fully passed).
        3. If passed: mark day as 'missed', then handle grace period logic.
    """
    from zoneinfo import ZoneInfo
    from datetime import datetime, time as dt_time

    now_utc = timezone.now()
    user_tz_cache = {}
    missed_count = 0
    grace_expired_count = 0

    # Step 1: Find uncompleted available days
    available_days = HealingDay.objects.filter(
        state='available',
        completed_at__isnull=True,
        theme__assessment__is_archived=False,
    ).select_related('user', 'user__healing_settings')

    for healing_day in available_days:
        user_id = healing_day.user_id

        if user_id not in user_tz_cache:
            try:
                settings_obj = healing_day.user.healing_settings
                user_tz_cache[user_id] = settings_obj.timezone
            except Exception:
                user_tz_cache[user_id] = 'UTC'

        try:
            user_tz = ZoneInfo(user_tz_cache[user_id])
        except Exception:
            user_tz = ZoneInfo('UTC')

        local_now = now_utc.astimezone(user_tz)
        local_today = local_now.date()

        # Step 2: Check if user's local date is strictly greater than unlock_date
        if local_today > healing_day.unlock_date:
            # Step 3: Mark as missed
            healing_day.state = 'missed'
            healing_day.save(update_fields=['state'])
            missed_count += 1

            # Handle grace period on streak
            try:
                streak = HealingStreak.objects.get(user_id=user_id)
            except HealingStreak.DoesNotExist:
                continue

            if not streak.grace_period_active:
                # First miss — activate grace period
                # Grace expires at 23:59:59 of tomorrow in user's local time
                from datetime import timedelta as td
                tomorrow_local = (local_now + td(days=1)).date()
                grace_local_dt = datetime.combine(
                    tomorrow_local, dt_time(23, 59, 59), tzinfo=user_tz
                )
                grace_expires_at_utc = grace_local_dt.astimezone(ZoneInfo('UTC'))

                streak.grace_period_active = True
                streak.grace_expires_at = grace_expires_at_utc
                streak.save(update_fields=['grace_period_active', 'grace_expires_at'])

                logger.info(
                    f"[Missed] Day {healing_day.day_number} missed for user {user_id}. "
                    f"Grace period activated until {grace_expires_at_utc}"
                )

    # Step 4: Check expired grace periods (separate pass)
    active_grace_streaks = HealingStreak.objects.filter(
        grace_period_active=True,
        grace_expires_at__isnull=False,
    )

    for streak in active_grace_streaks:
        if now_utc >= streak.grace_expires_at:
            # Grace window expired — zero the streak
            streak.current_streak = 0
            streak.grace_period_active = False
            streak.grace_expires_at = None
            streak.save(update_fields=[
                'current_streak', 'grace_period_active', 'grace_expires_at'
            ])
            grace_expired_count += 1
            logger.info(f"[Grace] Streak zeroed for user {streak.user_id} — grace expired")

    logger.info(
        f"[Missed] Marked {missed_count} days as missed. "
        f"Grace expired for {grace_expired_count} users."
    )
    return f"Missed: {missed_count}, Grace expired: {grace_expired_count}"


# ──────────────────────────────────────────────
# Task 9.6/9.8: send_healing_reminders
# ──────────────────────────────────────────────

@shared_task
def send_healing_reminders():
    """
    Send morning and evening healing reminders.

    Triggered by Celery Beat hourly (0 * * * *).
    Combines morning and evening checks into a single hourly pass.

    For each user with an active journey:
        - Converts current UTC time to user's local time.
        - If local hour matches morning_reminder_time.hour and morning enabled:
          sends morning reminder for uncompleted available day.
        - If local hour matches evening_reminder_time.hour and evening enabled:
          sends evening reminder for uncompleted available day.

    Respects both global (UserProfile.notifications_enabled) and
    journey-specific (HealingJourneySettings) preferences.
    """
    from zoneinfo import ZoneInfo
    from accounts.models import CustomUser

    now_utc = timezone.now()
    morning_count = 0
    evening_count = 0

    # Find users with active journeys (status='ready', not completed)
    active_assessments = HealingAssessment.objects.filter(
        status='ready',
        is_archived=False,
        journey_completed_at__isnull=True,
    ).select_related('user', 'user__healing_settings', 'user__profile')

    for assessment in active_assessments:
        user = assessment.user

        # Check global notification preference
        try:
            if not user.profile.notifications_enabled:
                continue
        except Exception:
            pass  # If no profile exists, proceed with defaults

        # Get journey settings
        try:
            settings_obj = user.healing_settings
        except Exception:
            continue

        try:
            user_tz = ZoneInfo(settings_obj.timezone)
        except Exception:
            user_tz = ZoneInfo('UTC')

        local_now = now_utc.astimezone(user_tz)
        local_hour = local_now.hour

        # Check for uncompleted available day today
        today_day = HealingDay.objects.filter(
            user=user,
            state='available',
            completed_at__isnull=True,
        ).order_by('day_number').first()

        if not today_day:
            continue

        # Morning reminder
        if (settings_obj.morning_reminder_enabled
                and local_hour == settings_obj.morning_reminder_time.hour):
            try:
                from notifications.helpers import create_notification
                create_notification(
                    user=user,
                    title='🌿 Your healing continues',
                    message=f'Day {today_day.day_number} is waiting for you. Your healing continues today.',
                    notif_type='healing_day_available',
                    data={'type': 'healing_morning_reminder', 'day_number': today_day.day_number},
                )
                morning_count += 1
            except Exception as e:
                logger.warning(f"[Reminder] Morning notification failed for user {user.id}: {e}")

        # Evening reminder
        if (settings_obj.evening_reminder_enabled
                and local_hour == settings_obj.evening_reminder_time.hour):
            try:
                from notifications.helpers import create_notification
                create_notification(
                    user=user,
                    title='🌙 Before the day ends',
                    message="10 minutes for yourself. You're worth it.",
                    notif_type='healing_evening_reminder',
                    data={'type': 'healing_evening_reminder', 'day_number': today_day.day_number},
                )
                evening_count += 1
            except Exception as e:
                logger.warning(f"[Reminder] Evening notification failed for user {user.id}: {e}")

    logger.info(
        f"[Reminders] Sent {morning_count} morning, {evening_count} evening reminders"
    )
    return f"Morning: {morning_count}, Evening: {evening_count}"

# ──────────────────────────────────────────────
# Task 9.7: extract_healing_reflection_memories
# ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def extract_healing_reflection_memories(self, reflection_id):
    """
    Extract memories from a user's Healing Journey reflection and save them to UserMemory.
    Provides the original mental exercise as context so the LLM understands what the user is answering.
    """
    try:
        from .models import HealingReflection
        from memory.models import UserMemory
        from memory.extractor import extract_memories
        from memory.vector_store import store_memory

        reflection = HealingReflection.objects.select_related('healing_day', 'user').get(id=reflection_id)
        
        if reflection.extracted_to_memory:
            return "Already extracted"

        user = reflection.user
        day = reflection.healing_day

        # Get context (what the user was asked to do)
        exercise_context = "No specific prompt found."
        if hasattr(day, 'content') and day.content:
            exercise_context = day.content.mental_workout

        # Format as conversation so the extractor understands context
        messages = [
            {
                "role": "model", 
                "content": f"Healing Journey Day {day.day_number} Mental Exercise:\n{exercise_context}"
            },
            {
                "role": "user", 
                "content": f"My Personal Reflection:\n{reflection.reflection_text}"
            }
        ]

        # Get existing memories for deduplication
        existing = list(
            UserMemory.objects.filter(user=user, is_active=True)
            .values_list('key', 'value')
        )
        existing_strings = [f"{k}: {v}" for k, v in existing]

        # Call the memory extractor
        result = extract_memories(messages, existing_memories=existing_strings)

        if not result or 'facts' not in result:
            logger.warning(f"Memory extraction returned no result for HealingReflection {reflection_id}")
            return "No result"

        memories_count = 0

        for fact in result.get('facts', []):
            category = fact.get('category', 'patterns')
            key = fact.get('key', '')
            value = fact.get('value', '')
            confidence = fact.get('confidence', 0.8)

            if not key or not value:
                continue

            # Note: source_conversation is left null because this comes from a Healing Journey reflection, not a chat.
            memory, created = UserMemory.objects.update_or_create(
                user=user,
                category=category,
                key=key,
                defaults={
                    'value': value,
                    'confidence': confidence,
                    'is_active': True,
                    'source_conversation': None,
                }
            )

            # Store in vector DB
            memory_text = f"{key.replace('_', ' ')}: {value}"
            store_memory(
                user_id=user.id,
                memory_id=f"memory_{memory.id}",
                text=memory_text,
                metadata={
                    'category': category,
                    'key': key,
                    'source': 'healing_reflection',
                    'healing_day': day.day_number,
                }
            )
            memories_count += 1

        # Mark as extracted
        reflection.extracted_to_memory = True
        reflection.save(update_fields=['extracted_to_memory'])

        logger.info(f"Extracted {memories_count} memories from HealingReflection {reflection_id}")
        return f"Extracted {memories_count} memories"

    except Exception as exc:
        logger.error(f"Failed to extract memory from reflection {reflection_id}: {exc}")
        raise self.retry(exc=exc)
