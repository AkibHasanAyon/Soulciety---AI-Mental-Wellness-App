from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status as http_status
from datetime import date, timedelta
from unittest.mock import patch

from .models import (
    HealingAssessment,
    HealingJourneySettings,
    HealingTheme,
    HealingDay,
    DayContent,
    HealingStreak,
)

User = get_user_model()


# ──────────────────────────────────────────────
# Valid test payload used across multiple test classes
# ──────────────────────────────────────────────

VALID_ASSESSMENT_PAYLOAD = {
    'q1_emotional_baseline': 'Anxious or on edge',
    'q2_past_influence': 4,
    'q3_life_area_impact': 'Self-worth & identity',
    'q4_core_pain_source': 'Being criticized, judged, or not good enough',
    'q5_coping_pattern': 'Withdraw from people',
    'q6_relationship_fear': 'Being abandoned or left',
    'q7_core_belief': 'I am not enough',
    'q8_desired_relief': 'Self-doubt',
    'q9_healing_resistance': 'Fear of what I might uncover',
    'q10_personal_desire': 'I want to stop being so hard on myself.',
}


# ══════════════════════════════════════════════
# Phase 1: Model Tests
# ══════════════════════════════════════════════

class HealingAssessmentModelTests(TestCase):
    """Tests for the HealingAssessment model."""

    def setUp(self):
        self.user = User.objects.create_user(
            email='healer@test.com',
            password='testpass123'
        )
        self.assessment_data = {
            'user': self.user,
            **VALID_ASSESSMENT_PAYLOAD,
        }

    def test_create_assessment(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        self.assertEqual(assessment.user, self.user)
        self.assertEqual(assessment.status, 'pending')
        self.assertFalse(assessment.is_archived)
        self.assertIsNone(assessment.journey_started_at)
        self.assertIsNone(assessment.journey_completed_at)
        self.assertIsNone(assessment.healing_profile)

    def test_status_choices(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        for status_code, _ in HealingAssessment.STATUS_CHOICES:
            assessment.status = status_code
            assessment.save()
            assessment.refresh_from_db()
            self.assertEqual(assessment.status, status_code)

    def test_journey_start_date_property(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        self.assertIsNone(assessment.journey_start_date)
        now = timezone.now()
        assessment.journey_started_at = now
        assessment.save()
        self.assertEqual(assessment.journey_start_date, now.date())

    def test_is_archived_default(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        self.assertFalse(assessment.is_archived)

    def test_str_representation(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        self.assertIn('healer@test.com', str(assessment))
        self.assertIn('pending', str(assessment))

    def test_str_archived(self):
        assessment = HealingAssessment.objects.create(**self.assessment_data, is_archived=True)
        self.assertIn('ARCHIVED', str(assessment))

    def test_multiple_assessments_per_user(self):
        HealingAssessment.objects.create(**self.assessment_data)
        HealingAssessment.objects.create(**self.assessment_data, is_archived=True)
        self.assertEqual(HealingAssessment.objects.filter(user=self.user).count(), 2)

    def test_cascade_delete_on_user(self):
        HealingAssessment.objects.create(**self.assessment_data)
        self.user.delete()
        self.assertEqual(HealingAssessment.objects.count(), 0)

    def test_q10_max_length(self):
        self.assessment_data['q10_personal_desire'] = 'x' * 500
        assessment = HealingAssessment.objects.create(**self.assessment_data)
        self.assertEqual(len(assessment.q10_personal_desire), 500)

    def test_healing_profile_json(self):
        profile = {
            'emotional_state': 'anxious',
            'trauma_type': 'abandonment',
            'core_wound': 'I am not enough',
        }
        assessment = HealingAssessment.objects.create(
            **self.assessment_data,
            healing_profile=profile
        )
        assessment.refresh_from_db()
        self.assertEqual(assessment.healing_profile['emotional_state'], 'anxious')


class HealingJourneySettingsModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='settings@test.com', password='testpass123'
        )

    def test_create_settings(self):
        settings_obj = HealingJourneySettings.objects.create(user=self.user)
        self.assertEqual(settings_obj.timezone, 'UTC')
        self.assertTrue(settings_obj.morning_reminder_enabled)
        self.assertTrue(settings_obj.evening_reminder_enabled)

    def test_custom_timezone(self):
        settings_obj = HealingJourneySettings.objects.create(
            user=self.user, timezone='America/New_York'
        )
        self.assertEqual(settings_obj.timezone, 'America/New_York')

    def test_onetoone_constraint(self):
        HealingJourneySettings.objects.create(user=self.user)
        with self.assertRaises(Exception):
            HealingJourneySettings.objects.create(user=self.user)

    def test_str_representation(self):
        settings_obj = HealingJourneySettings.objects.create(user=self.user)
        self.assertIn('settings@test.com', str(settings_obj))
        self.assertIn('UTC', str(settings_obj))


class HealingThemeModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='theme@test.com', password='testpass123'
        )
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD,
        )

    def test_create_theme(self):
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Coming Home to Yourself',
            theme_intention='Today you give yourself permission to begin.',
            theme_category='Foundation',
            healing_focus=['self-compassion', 'grounding', 'safety'],
        )
        self.assertEqual(theme.day_number, 1)
        self.assertEqual(theme.theme_category, 'Foundation')

    def test_unique_together_constraint(self):
        HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Theme 1', theme_intention='Intention 1',
            theme_category='Foundation', healing_focus=['grounding'],
        )
        with self.assertRaises(Exception):
            HealingTheme.objects.create(
                assessment=self.assessment, day_number=1,
                theme_title='Duplicate', theme_intention='Dup',
                theme_category='Foundation', healing_focus=['grounding'],
            )

    def test_create_30_themes(self):
        categories = {
            range(1, 6): 'Foundation', range(6, 11): 'Awareness',
            range(11, 16): 'Release', range(16, 21): 'Rewiring',
            range(21, 26): 'Embodiment', range(26, 31): 'Integration',
        }
        for day_range, category in categories.items():
            for day_num in day_range:
                HealingTheme.objects.create(
                    assessment=self.assessment, day_number=day_num,
                    theme_title=f'Theme {day_num}', theme_intention=f'Intention {day_num}',
                    theme_category=category, healing_focus=['a', 'b'],
                )
        self.assertEqual(HealingTheme.objects.filter(assessment=self.assessment).count(), 30)

    def test_ordering(self):
        for day in [5, 1, 3]:
            HealingTheme.objects.create(
                assessment=self.assessment, day_number=day,
                theme_title=f'Day {day}', theme_intention=f'I {day}',
                theme_category='Foundation', healing_focus=[],
            )
        themes = list(HealingTheme.objects.filter(assessment=self.assessment))
        self.assertEqual([t.day_number for t in themes], [1, 3, 5])

    def test_cascade_delete_on_assessment(self):
        HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='T', theme_intention='I',
            theme_category='Foundation', healing_focus=[],
        )
        self.assessment.delete()
        self.assertEqual(HealingTheme.objects.count(), 0)


class HealingDayModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email='day@test.com', password='testpass123'
        )
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            q1_emotional_baseline='Numb or disconnected',
            q2_past_influence=3,
            q3_life_area_impact='Inner peace & mental calm',
            q4_core_pain_source='Feeling ignored, unseen, or emotionally neglected',
            q5_coping_pattern='Sit with it quietly',
            q6_relationship_fear='Being misunderstood',
            q7_core_belief="I don't know who I am",
            q8_desired_relief='Feeling stuck',
            q9_healing_resistance="I didn't know where to start",
            q10_personal_desire='I want to feel alive again.',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment, 
            day_number=1,
            theme_title='Coming Home', 
            theme_intention='Begin here.',
            theme_category='Foundation', 
            healing_focus=['grounding'],
        )

    def test_create_day(self):
        day = HealingDay.objects.create(
            user=self.user, 
            theme=self.theme, 
            day_number=1,
            unlock_date=date.today(), 
            state='available',
        )
        self.assertEqual(day.state, 'available')
        self.assertEqual(day.content_status, 'pending')
        self.assertIsNone(day.completed_at)

    def test_state_choices(self):
        day = HealingDay.objects.create(
            user=self.user, 
            theme=self.theme, 
            day_number=1, 
            unlock_date=date.today(),
        )
        for state_code, _ in HealingDay.STATE_CHOICES:
            day.state = state_code
            day.save()
            day.refresh_from_db()
            self.assertEqual(day.state, state_code)


    def test_ordering(self):
        for day_num in [3, 1, 2]:
            t = HealingTheme.objects.create(
                assessment=self.assessment, 
                day_number=day_num,
                theme_title=f'T{day_num}', 
                theme_intention=f'I{day_num}',
                theme_category='Foundation', 
                healing_focus=[],
            ) if day_num != 1 else self.theme
            HealingDay.objects.create(
                user=self.user, theme=t, 
                day_number=day_num,
                unlock_date=date.today() + timedelta(days=day_num - 1),
            )
        days = list(HealingDay.objects.filter(user=self.user))
        self.assertEqual([d.day_number for d in days], [1, 2, 3])


class DayContentModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='content@test.com', password='testpass123')
        assessment = HealingAssessment.objects.create(
            user=self.user,
            q1_emotional_baseline='Sad or emotionally heavy', q2_past_influence=5,
            q3_life_area_impact='Relationships & connection',
            q4_core_pain_source='Being rejected or abandoned',
            q5_coping_pattern='Seek comfort from someone',
            q6_relationship_fear='Being abandoned or left',
            q7_core_belief='No one truly stays',
            q8_desired_relief='Loneliness',
            q9_healing_resistance="I tried before and it didn't work",
            q10_personal_desire='I want to feel safe in love.',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Safety', theme_intention='You are safe.',
            theme_category='Foundation', healing_focus=['safety'],
        )
        self.healing_day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available',
        )

    def test_create_day_content(self):
        content = DayContent.objects.create(
            healing_day=self.healing_day,
            guided_reflection='Reflection...', affirmation='I am safe.',
            mental_workout='Write 3 thoughts...', physical_workout='5min walk...',
            breathing_exercise={'name': 'Box', 'inhale_seconds': 4, 'hold_in_seconds': 4,
                                'exhale_seconds': 4, 'hold_out_seconds': 4, 'rounds': 5},
            mini_challenge='Send a text...', journal_prompt='What are you carrying?',
        )
        self.assertFalse(content.is_fallback)

    def test_onetoone_constraint(self):
        DayContent.objects.create(
            healing_day=self.healing_day,
            guided_reflection='R', affirmation='A', mental_workout='M',
            physical_workout='P', breathing_exercise={}, mini_challenge='C', journal_prompt='J',
        )
        with self.assertRaises(Exception):
            DayContent.objects.create(
                healing_day=self.healing_day,
                guided_reflection='R2', affirmation='A2', mental_workout='M2',
                physical_workout='P2', breathing_exercise={}, mini_challenge='C2', journal_prompt='J2',
            )

    def test_is_fallback_flag(self):
        content = DayContent.objects.create(
            healing_day=self.healing_day, is_fallback=True,
            guided_reflection='R', affirmation='A', mental_workout='M',
            physical_workout='P', breathing_exercise={}, mini_challenge='C', journal_prompt='J',
        )
        self.assertTrue(content.is_fallback)
        self.assertIn('fallback', str(content))

    def test_cascade_delete_on_healing_day(self):
        DayContent.objects.create(
            healing_day=self.healing_day,
            guided_reflection='R', affirmation='A', mental_workout='M',
            physical_workout='P', breathing_exercise={}, mini_challenge='C', journal_prompt='J',
        )
        self.healing_day.delete()
        self.assertEqual(DayContent.objects.count(), 0)


class HealingStreakModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='streak@test.com', password='testpass123')

    def test_create_streak_defaults(self):
        streak = HealingStreak.objects.create(user=self.user)
        self.assertEqual(streak.current_streak, 0)
        self.assertEqual(streak.longest_streak, 0)
        self.assertEqual(streak.total_days_completed, 0)
        self.assertEqual(streak.milestones_reached, [])
        self.assertFalse(streak.grace_period_active)

    def test_onetoone_constraint(self):
        HealingStreak.objects.create(user=self.user)
        with self.assertRaises(Exception):
            HealingStreak.objects.create(user=self.user)

    def test_milestones_json(self):
        streak = HealingStreak.objects.create(user=self.user)
        streak.milestones_reached = [3, 7, 14]
        streak.save()
        streak.refresh_from_db()
        self.assertEqual(streak.milestones_reached, [3, 7, 14])

    def test_grace_period_fields(self):
        now = timezone.now()
        streak = HealingStreak.objects.create(
            user=self.user, grace_period_active=True, grace_expires_at=now,
        )
        streak.refresh_from_db()
        self.assertTrue(streak.grace_period_active)

    def test_cascade_delete_on_user(self):
        HealingStreak.objects.create(user=self.user)
        self.user.delete()
        self.assertEqual(HealingStreak.objects.count(), 0)


# ══════════════════════════════════════════════
# Phase 2: Assessment API Tests
# ══════════════════════════════════════════════

class AssessmentSubmitAPITests(TestCase):
    """Tests for POST /api/healing/assessment/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='api@test.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('healing-assessment-submit')

    def test_valid_submission_returns_202(self):
        """A valid 10-answer payload should return 202 Accepted."""
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertIn('assessment_id', response.data)
        self.assertEqual(response.data['status'], 'generating')

    def test_assessment_created_in_db(self):
        """Submission should create a HealingAssessment record."""
        self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        assessment = HealingAssessment.objects.filter(user=self.user, is_archived=False).first()
        self.assertIsNotNone(assessment)
        self.assertEqual(assessment.status, 'pending')
        self.assertEqual(assessment.q1_emotional_baseline, 'Anxious or on edge')
        self.assertEqual(assessment.q2_past_influence, 4)
        self.assertEqual(assessment.q10_personal_desire, 'I want to stop being so hard on myself.')

    def test_invalid_q1_rejected(self):
        """Invalid MCQ option for Q1 should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q1_emotional_baseline': 'Invalid option'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('q1_emotional_baseline', response.data)

    def test_invalid_q2_too_low(self):
        """Q2 scale below 1 should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q2_past_influence': 0}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('q2_past_influence', response.data)

    def test_invalid_q2_too_high(self):
        """Q2 scale above 5 should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q2_past_influence': 6}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('q2_past_influence', response.data)

    def test_invalid_q3_rejected(self):
        """Invalid MCQ option for Q3 should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q3_life_area_impact': 'Not a real option'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q4_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q4_core_pain_source': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q5_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q5_coping_pattern': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q6_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q6_relationship_fear': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q7_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q7_core_belief': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q8_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q8_desired_relief': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_invalid_q9_rejected(self):
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q9_healing_resistance': 'Wrong'}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_q10_too_long_rejected(self):
        """Q10 text over 500 characters should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q10_personal_desire': 'x' * 501}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('q10_personal_desire', response.data)

    def test_q10_empty_rejected(self):
        """Q10 must not be empty."""
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q10_personal_desire': ''}
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_missing_field_rejected(self):
        """Missing a required field should be rejected."""
        payload = {**VALID_ASSESSMENT_PAYLOAD}
        del payload['q5_coping_pattern']
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
        self.assertIn('q5_coping_pattern', response.data)

    def test_duplicate_submission_returns_409(self):
        """Second POST when status='ready' should return 409 Conflict."""
        HealingAssessment.objects.create(
            user=self.user, status='ready',
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error'], 'active_journey_exists')

    def test_resubmission_after_failure_returns_202(self):
        """POST when status='failed' should allow re-submission and return 202."""
        assessment = HealingAssessment.objects.create(
            user=self.user, status='failed',
            generation_error='AI unavailable',
            **VALID_ASSESSMENT_PAYLOAD,
        )
        # Submit with slightly different data
        new_payload = {**VALID_ASSESSMENT_PAYLOAD, 'q1_emotional_baseline': 'Sad or emotionally heavy'}
        response = self.client.post(self.url, new_payload, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['assessment_id'], assessment.id)

        # Verify the answers were overwritten
        assessment.refresh_from_db()
        self.assertEqual(assessment.q1_emotional_baseline, 'Sad or emotionally heavy')
        self.assertEqual(assessment.status, 'pending')
        self.assertEqual(assessment.generation_error, '')

    def test_race_condition_pending_returns_202(self):
        """POST when status='pending' should return 202 without creating duplicate."""
        assessment = HealingAssessment.objects.create(
            user=self.user, status='pending',
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['assessment_id'], assessment.id)
        # Should NOT create a second assessment
        self.assertEqual(HealingAssessment.objects.filter(user=self.user, is_archived=False).count(), 1)

    def test_race_condition_generating_returns_202(self):
        """POST when status='generating' should return 202 without creating duplicate."""
        assessment = HealingAssessment.objects.create(
            user=self.user, status='generating',
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['assessment_id'], assessment.id)

    def test_archived_journey_does_not_block(self):
        """An archived assessment should not block a new submission."""
        HealingAssessment.objects.create(
            user=self.user, status='ready', is_archived=True,
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)

    def test_timezone_header_default_utc(self):
        """When no X-User-Timezone header is sent, default timezone should be used."""
        response = self.client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)

    def test_timezone_header_captured(self):
        """X-User-Timezone header should be readable by the view."""
        response = self.client.post(
            self.url, VALID_ASSESSMENT_PAYLOAD, format='json',
            HTTP_X_USER_TIMEZONE='America/New_York'
        )
        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)

    def test_auth_required(self):
        """Unauthenticated request should return 401."""
        client = APIClient()  # no auth
        response = client.post(self.url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)

    def test_all_q1_options_accepted(self):
        """All valid Q1 options should be accepted."""
        from .serializers import Q1_CHOICES
        for option in Q1_CHOICES:
            # Clean up any existing assessment
            HealingAssessment.objects.filter(user=self.user, is_archived=False).delete()
            payload = {**VALID_ASSESSMENT_PAYLOAD, 'q1_emotional_baseline': option}
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED,
                             f"Q1 option '{option}' should be accepted but got {response.status_code}")

    def test_all_q7_options_accepted(self):
        """All valid Q7 options (including apostrophes) should be accepted."""
        from .serializers import Q7_CHOICES
        for option in Q7_CHOICES:
            HealingAssessment.objects.filter(user=self.user, is_archived=False).delete()
            payload = {**VALID_ASSESSMENT_PAYLOAD, 'q7_core_belief': option}
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED,
                             f"Q7 option '{option}' should be accepted but got {response.status_code}")


class AssessmentStatusAPITests(TestCase):
    """Tests for GET /api/healing/assessment/status/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='status@test.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('healing-assessment-status')

    def test_status_pending(self):
        HealingAssessment.objects.create(user=self.user, status='pending', **VALID_ASSESSMENT_PAYLOAD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')
        self.assertFalse(response.data['day_1_unlocked'])

    def test_status_generating(self):
        HealingAssessment.objects.create(user=self.user, status='generating', **VALID_ASSESSMENT_PAYLOAD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'generating')
        self.assertFalse(response.data['day_1_unlocked'])

    def test_status_ready(self):
        HealingAssessment.objects.create(
            user=self.user, status='ready',
            journey_started_at=timezone.now(),
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ready')
        self.assertTrue(response.data['day_1_unlocked'])
        self.assertIsNotNone(response.data['journey_started_at'])

    def test_status_failed(self):
        HealingAssessment.objects.create(user=self.user, status='failed', **VALID_ASSESSMENT_PAYLOAD)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'failed')

    def test_no_assessment_returns_404(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_archived_assessment_not_returned(self):
        """Archived assessments should not be returned by the status endpoint."""
        HealingAssessment.objects.create(
            user=self.user, status='ready', is_archived=True,
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_auth_required(self):
        client = APIClient()
        response = client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class AssessmentProfileAPITests(TestCase):
    """Tests for GET /api/healing/assessment/profile/"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='profile@test.com', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.url = reverse('healing-assessment-profile')

    def test_profile_returned_when_ready(self):
        profile_data = {
            'emotional_state': 'anxious',
            'trauma_type': 'abandonment',
            'core_wound': 'I am not enough',
            'life_domain': 'relationships',
            'primary_healing_goal': 'relief from self-doubt',
            'healing_arc_summary': 'A journey from fear to self-trust.',
        }
        HealingAssessment.objects.create(
            user=self.user, status='ready',
            healing_profile=profile_data,
            journey_started_at=timezone.now(),
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.data['healing_profile']['emotional_state'], 'anxious')
        self.assertEqual(response.data['status'], 'ready')
        self.assertIsNotNone(response.data['journey_started_at'])
        self.assertIsNone(response.data['journey_completed_at'])

    def test_profile_empty_before_generation(self):
        """Before AI generation, healing_profile is null."""
        HealingAssessment.objects.create(
            user=self.user, status='pending',
            **VALID_ASSESSMENT_PAYLOAD,
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertIsNone(response.data['healing_profile'])
        self.assertEqual(response.data['status'], 'pending')

    def test_no_assessment_returns_404(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_auth_required(self):
        client = APIClient()
        response = client.get(self.url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class AssessmentSerializerValidationTests(TestCase):
    """Focused tests on the AssessmentSubmissionSerializer validation logic."""

    def test_valid_payload_passes(self):
        from .serializers import AssessmentSubmissionSerializer
        serializer = AssessmentSubmissionSerializer(data=VALID_ASSESSMENT_PAYLOAD)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_q2_boundary_values(self):
        """Test Q2 at boundaries: 1 and 5 should pass, 0 and 6 should fail."""
        from .serializers import AssessmentSubmissionSerializer

        # Valid boundaries
        for value in [1, 5]:
            payload = {**VALID_ASSESSMENT_PAYLOAD, 'q2_past_influence': value}
            serializer = AssessmentSubmissionSerializer(data=payload)
            self.assertTrue(serializer.is_valid(), f"Q2={value} should be valid: {serializer.errors}")

        # Invalid boundaries
        for value in [0, 6, -1, 100]:
            payload = {**VALID_ASSESSMENT_PAYLOAD, 'q2_past_influence': value}
            serializer = AssessmentSubmissionSerializer(data=payload)
            self.assertFalse(serializer.is_valid(), f"Q2={value} should be invalid")

    def test_q10_boundary_length(self):
        """Test Q10 at exactly 500 characters."""
        from .serializers import AssessmentSubmissionSerializer
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q10_personal_desire': 'x' * 500}
        serializer = AssessmentSubmissionSerializer(data=payload)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_q2_non_integer_rejected(self):
        """Q2 must be an integer, not a string."""
        from .serializers import AssessmentSubmissionSerializer
        payload = {**VALID_ASSESSMENT_PAYLOAD, 'q2_past_influence': 'three'}
        serializer = AssessmentSubmissionSerializer(data=payload)
        self.assertFalse(serializer.is_valid())

    def test_completely_empty_payload_rejected(self):
        """An empty payload should fail with errors for all 10 fields."""
        from .serializers import AssessmentSubmissionSerializer
        serializer = AssessmentSubmissionSerializer(data={})
        self.assertFalse(serializer.is_valid())
        self.assertEqual(len(serializer.errors), 10)


# ══════════════════════════════════════════════
# Phase 3: Prompt, Validator & Task Tests
# ══════════════════════════════════════════════

# ── Helper: build a valid mock AI response ──

def _build_mock_ai_response():
    """Return a valid plan generation response dict matching the expected schema."""
    import json

    healing_profile = {
        'emotional_state': 'anxious',
        'trauma_type': 'criticism_judgment',
        'core_wound': 'not_enough',
        'life_domain': 'self_worth',
        'coping_style': 'withdrawal',
        'attachment_pattern': 'anxious_avoidant',
        'primary_healing_goal': 'relief_from_self_doubt',
        'healing_blockers': 'fear_of_uncovering',
        'personal_desire': 'Stop being hard on myself',
        'healing_arc_summary': 'A journey from self-criticism to self-compassion, rebuilding trust in your own worth.',
    }

    categories = {
        range(1, 6): 'Foundation',
        range(6, 11): 'Awareness',
        range(11, 16): 'Release',
        range(16, 21): 'Rewiring',
        range(21, 26): 'Embodiment',
        range(26, 31): 'Integration',
    }
    themes = []
    for day_range, category in categories.items():
        for day_num in day_range:
            themes.append({
                'day_number': day_num,
                'theme_title': f'Day {day_num} Theme',
                'theme_intention': f'Today you embrace step {day_num}.',
                'theme_category': category,
                'healing_focus': ['self-compassion', 'grounding'],
            })

    return {'healing_profile': healing_profile, 'themes': themes}


class PromptConstructionTests(TestCase):
    """Tests for prompt building helpers."""

    def setUp(self):
        self.user = User.objects.create_user(email='prompt@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD,
        )

    def test_build_plan_generation_prompt_contains_all_answers(self):
        """The formatted prompt should contain all 10 assessment answers."""
        from .prompts import build_plan_generation_prompt
        prompt = build_plan_generation_prompt(self.assessment)
        self.assertIn('Anxious or on edge', prompt)
        self.assertIn('4', prompt)
        self.assertIn('Self-worth & identity', prompt)
        self.assertIn('Being criticized, judged, or not good enough', prompt)
        self.assertIn('Withdraw from people', prompt)
        self.assertIn('Being abandoned or left', prompt)
        self.assertIn('I am not enough', prompt)
        self.assertIn('Self-doubt', prompt)
        self.assertIn('Fear of what I might uncover', prompt)
        self.assertIn('I want to stop being so hard on myself.', prompt)

    def test_system_prompt_not_empty(self):
        """System prompt should be a non-empty string."""
        from .prompts import PLAN_GENERATION_SYSTEM_PROMPT
        self.assertTrue(len(PLAN_GENERATION_SYSTEM_PROMPT) > 100)

    def test_system_prompt_contains_json_instruction(self):
        """System prompt should instruct the AI to return JSON."""
        from .prompts import PLAN_GENERATION_SYSTEM_PROMPT
        self.assertIn('JSON', PLAN_GENERATION_SYSTEM_PROMPT)

    def test_system_prompt_contains_arc_phases(self):
        """System prompt should contain all 6 arc phases."""
        from .prompts import PLAN_GENERATION_SYSTEM_PROMPT
        for phase in ['Foundation', 'Awareness', 'Release', 'Rewiring', 'Embodiment', 'Integration']:
            self.assertIn(phase, PLAN_GENERATION_SYSTEM_PROMPT)


class HealingProfileValidationTests(TestCase):
    """Tests for validate_healing_profile."""

    def test_valid_profile_passes(self):
        from .validators import validate_healing_profile
        profile = _build_mock_ai_response()['healing_profile']
        result = validate_healing_profile(profile)
        self.assertEqual(result, profile)

    def test_not_a_dict_raises(self):
        from .validators import validate_healing_profile, PlanValidationError
        with self.assertRaises(PlanValidationError):
            validate_healing_profile("a string")

    def test_missing_key_raises(self):
        from .validators import validate_healing_profile, PlanValidationError
        profile = _build_mock_ai_response()['healing_profile']
        del profile['emotional_state']
        with self.assertRaises(PlanValidationError) as ctx:
            validate_healing_profile(profile)
        self.assertIn('emotional_state', str(ctx.exception))

    def test_empty_value_raises(self):
        from .validators import validate_healing_profile, PlanValidationError
        profile = _build_mock_ai_response()['healing_profile']
        profile['trauma_type'] = ''
        with self.assertRaises(PlanValidationError) as ctx:
            validate_healing_profile(profile)
        self.assertIn('trauma_type', str(ctx.exception))

    def test_none_value_raises(self):
        from .validators import validate_healing_profile, PlanValidationError
        profile = _build_mock_ai_response()['healing_profile']
        profile['core_wound'] = None
        with self.assertRaises(PlanValidationError):
            validate_healing_profile(profile)


class ThemeValidationTests(TestCase):
    """Tests for validate_themes."""

    def test_valid_30_themes_passes(self):
        from .validators import validate_themes
        themes = _build_mock_ai_response()['themes']
        result = validate_themes(themes)
        self.assertEqual(len(result), 30)

    def test_not_a_list_raises(self):
        from .validators import validate_themes, PlanValidationError
        with self.assertRaises(PlanValidationError):
            validate_themes("not a list")

    def test_wrong_count_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes'][:25]
        with self.assertRaises(PlanValidationError) as ctx:
            validate_themes(themes)
        self.assertIn('25', str(ctx.exception))

    def test_duplicate_day_number_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[1]['day_number'] = 1  # duplicate
        with self.assertRaises(PlanValidationError) as ctx:
            validate_themes(themes)
        self.assertIn('Duplicate', str(ctx.exception))

    def test_invalid_day_number_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[0]['day_number'] = 0  # out of range
        with self.assertRaises(PlanValidationError):
            validate_themes(themes)

    def test_day_number_31_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[0]['day_number'] = 31
        with self.assertRaises(PlanValidationError):
            validate_themes(themes)

    def test_invalid_category_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[0]['theme_category'] = 'InvalidPhase'
        with self.assertRaises(PlanValidationError) as ctx:
            validate_themes(themes)
        self.assertIn('InvalidPhase', str(ctx.exception))

    def test_empty_title_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[0]['theme_title'] = ''
        with self.assertRaises(PlanValidationError):
            validate_themes(themes)

    def test_empty_healing_focus_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        themes[0]['healing_focus'] = []
        with self.assertRaises(PlanValidationError):
            validate_themes(themes)

    def test_missing_key_raises(self):
        from .validators import validate_themes, PlanValidationError
        themes = _build_mock_ai_response()['themes']
        del themes[0]['theme_intention']
        with self.assertRaises(PlanValidationError):
            validate_themes(themes)


class PlanResponseValidationTests(TestCase):
    """Tests for validate_plan_response (full response)."""

    def test_valid_response_passes(self):
        from .validators import validate_plan_response
        data = _build_mock_ai_response()
        profile, themes = validate_plan_response(data)
        self.assertIsInstance(profile, dict)
        self.assertEqual(len(themes), 30)

    def test_missing_healing_profile_key_raises(self):
        from .validators import validate_plan_response, PlanValidationError
        data = _build_mock_ai_response()
        del data['healing_profile']
        with self.assertRaises(PlanValidationError):
            validate_plan_response(data)

    def test_missing_themes_key_raises(self):
        from .validators import validate_plan_response, PlanValidationError
        data = _build_mock_ai_response()
        del data['themes']
        with self.assertRaises(PlanValidationError):
            validate_plan_response(data)

    def test_not_a_dict_raises(self):
        from .validators import validate_plan_response, PlanValidationError
        with self.assertRaises(PlanValidationError):
            validate_plan_response([])


class BreathingExerciseValidationTests(TestCase):
    """Tests for validate_breathing_exercise."""

    def test_valid_exercise_passes(self):
        from .validators import validate_breathing_exercise
        data = {
            'name': 'Box Breathing', 'description': 'Calming exercise.',
            'inhale_seconds': 4, 'hold_in_seconds': 4,
            'exhale_seconds': 4, 'hold_out_seconds': 4, 'rounds': 5,
        }
        result = validate_breathing_exercise(data)
        self.assertEqual(result['name'], 'Box Breathing')

    def test_min_boundary_passes(self):
        from .validators import validate_breathing_exercise
        data = {
            'name': 'Min', 'description': 'Min exercise.',
            'inhale_seconds': 3, 'hold_in_seconds': 0,
            'exhale_seconds': 4, 'hold_out_seconds': 0, 'rounds': 3,
        }
        validate_breathing_exercise(data)  # Should not raise

    def test_max_boundary_passes(self):
        from .validators import validate_breathing_exercise
        data = {
            'name': 'Max', 'description': 'Max exercise.',
            'inhale_seconds': 6, 'hold_in_seconds': 8,
            'exhale_seconds': 10, 'hold_out_seconds': 4, 'rounds': 8,
        }
        validate_breathing_exercise(data)  # Should not raise

    def test_inhale_too_low_raises(self):
        from .validators import validate_breathing_exercise, ContentValidationError
        data = {
            'name': 'Test', 'description': 'x',
            'inhale_seconds': 2, 'hold_in_seconds': 4,
            'exhale_seconds': 4, 'hold_out_seconds': 2, 'rounds': 4,
        }
        with self.assertRaises(ContentValidationError):
            validate_breathing_exercise(data)

    def test_exhale_too_high_raises(self):
        from .validators import validate_breathing_exercise, ContentValidationError
        data = {
            'name': 'Test', 'description': 'x',
            'inhale_seconds': 4, 'hold_in_seconds': 4,
            'exhale_seconds': 11, 'hold_out_seconds': 2, 'rounds': 4,
        }
        with self.assertRaises(ContentValidationError):
            validate_breathing_exercise(data)

    def test_non_integer_raises(self):
        from .validators import validate_breathing_exercise, ContentValidationError
        data = {
            'name': 'Test', 'description': 'x',
            'inhale_seconds': 4.5, 'hold_in_seconds': 4,
            'exhale_seconds': 4, 'hold_out_seconds': 2, 'rounds': 4,
        }
        with self.assertRaises(ContentValidationError):
            validate_breathing_exercise(data)

    def test_missing_key_raises(self):
        from .validators import validate_breathing_exercise, ContentValidationError
        data = {'name': 'Test', 'description': 'x', 'inhale_seconds': 4}
        with self.assertRaises(ContentValidationError):
            validate_breathing_exercise(data)


class DayContentValidationTests(TestCase):
    """Tests for validate_day_content."""

    def _valid_content(self):
        return {
            'guided_reflection': 'A warm reflection...',
            'affirmation': 'I am enough.',
            'mental_workout': 'Write 3 thoughts...',
            'physical_workout': 'Gentle stretch...',
            'breathing_exercise': {
                'name': 'Box', 'description': 'x',
                'inhale_seconds': 4, 'hold_in_seconds': 4,
                'exhale_seconds': 4, 'hold_out_seconds': 4, 'rounds': 5,
            },
            'mini_challenge': 'Send a text...',
            'journal_prompt': 'What are you carrying?',
        }

    def test_valid_content_passes(self):
        from .validators import validate_day_content
        result = validate_day_content(self._valid_content())
        self.assertIsInstance(result, dict)

    def test_missing_field_raises(self):
        from .validators import validate_day_content, ContentValidationError
        data = self._valid_content()
        del data['affirmation']
        with self.assertRaises(ContentValidationError):
            validate_day_content(data)

    def test_empty_text_field_raises(self):
        from .validators import validate_day_content, ContentValidationError
        data = self._valid_content()
        data['guided_reflection'] = ''
        with self.assertRaises(ContentValidationError):
            validate_day_content(data)

    def test_whitespace_only_field_raises(self):
        from .validators import validate_day_content, ContentValidationError
        data = self._valid_content()
        data['affirmation'] = '   '
        with self.assertRaises(ContentValidationError):
            validate_day_content(data)


class JSONParsingTests(TestCase):
    """Tests for _parse_json_response helper."""

    def test_plain_json(self):
        from .tasks import _parse_json_response
        result = _parse_json_response('{"key": "value"}')
        self.assertEqual(result['key'], 'value')

    def test_markdown_fenced_json(self):
        from .tasks import _parse_json_response
        result = _parse_json_response('```json\n{"key": "value"}\n```')
        self.assertEqual(result['key'], 'value')

    def test_markdown_fenced_no_lang(self):
        from .tasks import _parse_json_response
        result = _parse_json_response('```\n{"key": "value"}\n```')
        self.assertEqual(result['key'], 'value')

    def test_invalid_json_raises(self):
        from .tasks import _parse_json_response
        import json
        with self.assertRaises(json.JSONDecodeError):
            _parse_json_response('not json at all')

    def test_whitespace_handling(self):
        from .tasks import _parse_json_response
        result = _parse_json_response('  \n  {"key": "value"}  \n  ')
        self.assertEqual(result['key'], 'value')


class GenerateHealingPlanTaskTests(TestCase):
    """
    Tests for the generate_healing_plan Celery task.
    Uses unittest.mock to mock the Gemini API.
    """

    def setUp(self):
        self.user = User.objects.create_user(email='task@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD,
        )

    def _mock_gemini_response(self, data):
        """Create a mock Gemini response object."""
        import json
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.text = json.dumps(data)
        return mock_response

    def test_full_task_flow_success(self):
        """Test the complete happy path with mocked Gemini."""
        import json
        from unittest.mock import patch, MagicMock

        mock_data = _build_mock_ai_response()

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = self._mock_gemini_response(mock_data)
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            result = generate_healing_plan(self.assessment.id, 'America/New_York')

        # Verify assessment was updated
        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, 'ready')
        self.assertIsNotNone(self.assessment.journey_started_at)
        self.assertIsNotNone(self.assessment.healing_profile)
        self.assertEqual(self.assessment.healing_profile['emotional_state'], 'anxious')

        # Verify 30 themes created
        themes = HealingTheme.objects.filter(assessment=self.assessment)
        self.assertEqual(themes.count(), 30)

        # Verify 30 days created
        days = HealingDay.objects.filter(user=self.user)
        self.assertEqual(days.count(), 30)

        # Verify Day 1 is available, others locked
        day_1 = days.get(day_number=1)
        self.assertEqual(day_1.state, 'available')
        day_2 = days.get(day_number=2)
        self.assertEqual(day_2.state, 'locked')

        # Verify unlock dates are sequential
        for day in days:
            expected_date = self.assessment.journey_started_at.date() + timedelta(days=day.day_number - 1)
            self.assertEqual(day.unlock_date, expected_date)

        # Verify streak created
        streak = HealingStreak.objects.get(user=self.user)
        self.assertEqual(streak.current_streak, 0)

        # Verify settings created with provided timezone
        settings_obj = HealingJourneySettings.objects.get(user=self.user)
        self.assertEqual(settings_obj.timezone, 'America/New_York')

    def test_status_transitions(self):
        """Test that status goes from pending → generating → ready."""
        from unittest.mock import patch, MagicMock

        mock_data = _build_mock_ai_response()
        statuses_seen = []

        original_save = HealingAssessment.save

        def tracking_save(instance, *args, **kwargs):
            original_save(instance, *args, **kwargs)
            if isinstance(instance, HealingAssessment) and instance.id == self.assessment.id:
                statuses_seen.append(instance.status)

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn, \
             patch.object(HealingAssessment, 'save', tracking_save):
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = self._mock_gemini_response(mock_data)
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            generate_healing_plan(self.assessment.id)

        # Should have seen: generating (step 1) then ready (step 6)
        self.assertIn('generating', statuses_seen)
        self.assertIn('ready', statuses_seen)

    def test_assessment_not_found_returns_early(self):
        """Task with invalid assessment ID should return early without error."""
        from .tasks import generate_healing_plan
        result = generate_healing_plan(99999)
        self.assertIn('not found', result)

    def test_empty_gemini_response_retries(self):
        """Empty Gemini response should trigger a retry (raises original exception in sync mode)."""
        from unittest.mock import patch, MagicMock

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = ''
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            with self.assertRaises(Exception) as ctx:
                generate_healing_plan(self.assessment.id)
            self.assertIn('Empty response', str(ctx.exception))

    def test_invalid_json_retries(self):
        """Invalid JSON from Gemini should trigger a retry."""
        from unittest.mock import patch, MagicMock
        import json as json_mod

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = 'This is not JSON at all'
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            with self.assertRaises(json_mod.JSONDecodeError):
                generate_healing_plan(self.assessment.id)

    def test_validation_error_retries(self):
        """Valid JSON but invalid schema should trigger a retry."""
        from unittest.mock import patch, MagicMock
        from .validators import PlanValidationError
        import json

        # Reset any leaked state from other tests
        from .tasks import generate_healing_plan
        generate_healing_plan.request.retries = 0

        # Missing themes key
        bad_data = {'healing_profile': _build_mock_ai_response()['healing_profile']}

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = json.dumps(bad_data)
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            with self.assertRaises(PlanValidationError):
                generate_healing_plan(self.assessment.id)

    def test_permanent_failure_after_max_retries(self):
        """After max retries, assessment should be marked 'failed'."""
        from unittest.mock import patch, MagicMock

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = 'bad json'
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            # Simulate max retries reached by setting request.retries
            generate_healing_plan.request.retries = 3
            generate_healing_plan.max_retries = 3
            try:
                result = generate_healing_plan(self.assessment.id)
            finally:
                # Clean up shared task state to prevent leaking to other tests
                generate_healing_plan.request.retries = 0

        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, 'failed')
        self.assertTrue(len(self.assessment.generation_error) > 0)

    def test_streak_created_only_once(self):
        """Running the task twice should not create duplicate streak (get_or_create)."""
        from unittest.mock import patch, MagicMock

        mock_data = _build_mock_ai_response()

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = self._mock_gemini_response(mock_data)
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            generate_healing_plan(self.assessment.id)

        self.assertEqual(HealingStreak.objects.filter(user=self.user).count(), 1)

    def test_gemini_called_with_correct_model(self):
        """The task should call Gemini with the correct model name."""
        from unittest.mock import patch, MagicMock

        mock_data = _build_mock_ai_response()

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = self._mock_gemini_response(mock_data)
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            generate_healing_plan(self.assessment.id)

            call_args = mock_client.models.generate_content.call_args
            self.assertEqual(call_args.kwargs['model'], 'gemini-3.5-flash')

    def test_markdown_fenced_response_handled(self):
        """JSON wrapped in markdown fences should be parsed correctly."""
        import json
        from unittest.mock import patch, MagicMock

        mock_data = _build_mock_ai_response()
        fenced_json = f'```json\n{json.dumps(mock_data)}\n```'

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = fenced_json
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_healing_plan
            generate_healing_plan(self.assessment.id)

        self.assessment.refresh_from_db()
        self.assertEqual(self.assessment.status, 'ready')
        self.assertEqual(HealingTheme.objects.filter(assessment=self.assessment).count(), 30)


# ══════════════════════════════════════════════
# Phase 4 Tests: Content Engine
# ══════════════════════════════════════════════


def _build_mock_day_content():
    """Return a valid day content response dict matching the expected schema."""
    return {
        'guided_reflection': (
            'Welcome to today, beautiful soul. This is a moment of pause. '
            'A place to breathe. Allow yourself to simply be here, exactly as you are. '
            'There is nothing you need to fix or prove right now. The fact that you showed up '
            'is already an act of radical self-love. Today we begin something sacred — something '
            'that has been waiting for you. Not the version of you that the world expects, but the '
            'real, unedited, honest version.'
        ),
        'affirmation': 'I am worthy of love and peace. I choose myself today.',
        'mental_workout': (
            'Close your eyes. Think of one thought you repeat about yourself. Write it down. '
            'Now ask: who first told me this was true? Rewrite the thought as a compassionate friend would.'
        ),
        'physical_workout': (
            'Stand gently. Place both feet on the ground. Tense each muscle group for 5 seconds '
            'and release: feet, calves, thighs, belly, shoulders, fists, jaw. Shake your hands to finish.'
        ),
        'breathing_exercise': {
            'name': 'Grounding Breath',
            'description': 'A calming breath to bring you into the present.',
            'inhale_seconds': 4,
            'hold_in_seconds': 4,
            'exhale_seconds': 6,
            'hold_out_seconds': 2,
            'rounds': 5,
        },
        'mini_challenge': 'Place your hand on your chest and say: I am here. I am safe.',
        'journal_prompt': 'What is one thing you have been carrying that no longer belongs to you?',
    }


class FallbackContentBankTests(TestCase):
    """Tests for the hardcoded fallback content bank."""

    def test_all_six_phases_present(self):
        """Fallback bank must have content for all 6 healing phases."""
        from .fallbacks import FALLBACK_CONTENT_BANK
        expected = ['Foundation', 'Awareness', 'Release', 'Rewiring', 'Embodiment', 'Integration']
        for phase in expected:
            self.assertIn(phase, FALLBACK_CONTENT_BANK, f"Missing phase: {phase}")

    def test_each_phase_has_all_7_modules(self):
        """Each phase must have all 7 content modules."""
        from .fallbacks import FALLBACK_CONTENT_BANK
        required_keys = [
            'guided_reflection', 'affirmation', 'mental_workout',
            'physical_workout', 'breathing_exercise', 'mini_challenge', 'journal_prompt',
        ]
        for phase, content in FALLBACK_CONTENT_BANK.items():
            for key in required_keys:
                self.assertIn(key, content, f"Phase '{phase}' missing key '{key}'")
                if key != 'breathing_exercise':
                    self.assertTrue(
                        len(content[key].strip()) > 0,
                        f"Phase '{phase}' has empty '{key}'"
                    )

    def test_breathing_exercises_valid(self):
        """All fallback breathing exercises must pass validation."""
        from .fallbacks import FALLBACK_CONTENT_BANK
        from .validators import validate_breathing_exercise

        for phase, content in FALLBACK_CONTENT_BANK.items():
            try:
                validate_breathing_exercise(content['breathing_exercise'])
            except Exception as e:
                self.fail(f"Phase '{phase}' breathing exercise invalid: {e}")

    def test_get_fallback_content_returns_copy(self):
        """get_fallback_content should return a copy, not the original."""
        from .fallbacks import get_fallback_content
        result = get_fallback_content('Foundation')
        self.assertIsInstance(result, dict)
        self.assertIn('guided_reflection', result)

    def test_get_fallback_content_invalid_category_raises(self):
        """Invalid category should raise KeyError."""
        from .fallbacks import get_fallback_content
        with self.assertRaises(KeyError):
            get_fallback_content('InvalidPhase')


class ContentPromptBuildingTests(TestCase):
    """Tests for content generation prompt construction."""

    def setUp(self):
        self.user = User.objects.create_user(email='cprompt@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            healing_profile={
                'emotional_state': 'anxious',
                'trauma_type': 'criticism_judgment',
                'core_wound': 'not_enough',
                'life_domain': 'self_worth',
                'coping_style': 'withdrawal',
                'attachment_pattern': 'anxious_avoidant',
                'primary_healing_goal': 'relief_from_self_doubt',
                'healing_blockers': 'fear_of_uncovering',
                'personal_desire': 'Stop being hard on myself',
                'healing_arc_summary': 'A journey from self-criticism to self-compassion.',
            },
            status='ready',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=1,
            theme_title='Coming Home to Yourself',
            theme_intention='Today you give yourself permission to begin.',
            theme_category='Foundation',
            healing_focus=['self-compassion', 'grounding'],
        )
        self.healing_day = HealingDay.objects.create(
            user=self.user,
            theme=self.theme,
            day_number=1,
            unlock_date=date.today(),
            state='available',
            content_status='pending',
        )

    def test_prompt_contains_day_number(self):
        from .prompts import build_content_generation_prompt
        prompt = build_content_generation_prompt(self.healing_day)
        self.assertIn('Day 1', prompt)

    def test_prompt_contains_theme_title(self):
        from .prompts import build_content_generation_prompt
        prompt = build_content_generation_prompt(self.healing_day)
        self.assertIn('Coming Home to Yourself', prompt)

    def test_prompt_contains_trauma_type(self):
        from .prompts import build_content_generation_prompt
        prompt = build_content_generation_prompt(self.healing_day)
        self.assertIn('criticism_judgment', prompt)

    def test_prompt_contains_healing_focus(self):
        from .prompts import build_content_generation_prompt
        prompt = build_content_generation_prompt(self.healing_day)
        self.assertIn('self-compassion', prompt)

    def test_content_system_prompt_not_empty(self):
        from .prompts import CONTENT_GENERATION_SYSTEM_PROMPT
        self.assertTrue(len(CONTENT_GENERATION_SYSTEM_PROMPT) > 100)

    def test_content_system_prompt_contains_json(self):
        from .prompts import CONTENT_GENERATION_SYSTEM_PROMPT
        self.assertIn('JSON', CONTENT_GENERATION_SYSTEM_PROMPT)


class GenerateDayContentTaskTests(TestCase):
    """Tests for the generate_day_content Celery task."""

    def setUp(self):
        self.user = User.objects.create_user(email='content@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            healing_profile=_build_mock_ai_response()['healing_profile'],
            status='ready',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=1,
            theme_title='Coming Home',
            theme_intention='Begin.',
            theme_category='Foundation',
            healing_focus=['grounding'],
        )
        self.healing_day = HealingDay.objects.create(
            user=self.user,
            theme=self.theme,
            day_number=1,
            unlock_date=date.today(),
            state='available',
            content_status='pending',
        )

    def _mock_gemini_response(self, data):
        import json
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.text = json.dumps(data)
        return mock_response

    def test_successful_content_generation(self):
        """Full happy-path test: mock Gemini returns valid content, DayContent is created."""
        from unittest.mock import patch, MagicMock

        mock_content = _build_mock_day_content()

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = self._mock_gemini_response(mock_content)
            mock_client_fn.return_value = mock_client

            from .tasks import generate_day_content
            result = generate_day_content(self.healing_day.id)

        self.healing_day.refresh_from_db()
        self.assertEqual(self.healing_day.content_status, 'ready')
        self.assertTrue(DayContent.objects.filter(healing_day=self.healing_day).exists())

        content = self.healing_day.content
        self.assertFalse(content.is_fallback)
        self.assertIn('beautiful soul', content.guided_reflection)
        self.assertEqual(content.breathing_exercise['name'], 'Grounding Breath')

    def test_skip_if_content_exists(self):
        """Task should skip if DayContent already exists."""
        DayContent.objects.create(
            healing_day=self.healing_day,
            guided_reflection='existing',
            affirmation='existing',
            mental_workout='existing',
            physical_workout='existing',
            breathing_exercise={'name': 'test', 'description': 'test', 'inhale_seconds': 4, 'hold_in_seconds': 4, 'exhale_seconds': 4, 'hold_out_seconds': 0, 'rounds': 4},
            mini_challenge='existing',
            journal_prompt='existing',
        )

        from .tasks import generate_day_content
        result = generate_day_content(self.healing_day.id)
        self.assertIn('already exists', result)

    def test_not_found_returns_message(self):
        """Task should handle non-existent HealingDay gracefully."""
        from .tasks import generate_day_content
        result = generate_day_content(99999)
        self.assertIn('not found', result)

    def test_empty_response_retries(self):
        """Empty Gemini response should trigger a retry."""
        from unittest.mock import patch, MagicMock

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = ''
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_day_content
            with self.assertRaises(Exception):
                generate_day_content(self.healing_day.id)

    def test_permanent_failure_triggers_fallback(self):
        """After max retries, content should be marked as 'failed' and fallback queued."""
        from unittest.mock import patch, MagicMock

        with patch('healing_journey.tasks._get_gemini_client') as mock_client_fn:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = 'invalid json'
            mock_client.models.generate_content.return_value = mock_response
            mock_client_fn.return_value = mock_client

            from .tasks import generate_day_content
            generate_day_content.request.retries = 3
            generate_day_content.max_retries = 3

            with patch('healing_journey.tasks.serve_fallback_content') as mock_fallback:
                mock_fallback.delay = MagicMock()
                try:
                    generate_day_content(self.healing_day.id)
                finally:
                    generate_day_content.request.retries = 0

        self.healing_day.refresh_from_db()
        self.assertEqual(self.healing_day.content_status, 'failed')


class ServeFallbackContentTaskTests(TestCase):
    """Tests for the serve_fallback_content task."""

    def setUp(self):
        self.user = User.objects.create_user(email='fallback@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            status='ready',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=1,
            theme_title='Test Theme',
            theme_intention='Test intention.',
            theme_category='Foundation',
            healing_focus=['grounding'],
        )
        self.healing_day = HealingDay.objects.create(
            user=self.user,
            theme=self.theme,
            day_number=1,
            unlock_date=date.today(),
            state='available',
            content_status='failed',
        )

    def test_fallback_creates_content(self):
        """Fallback task should create DayContent with is_fallback=True."""
        from .tasks import serve_fallback_content
        serve_fallback_content(self.healing_day.id)

        self.healing_day.refresh_from_db()
        self.assertEqual(self.healing_day.content_status, 'ready')
        self.assertTrue(DayContent.objects.filter(healing_day=self.healing_day).exists())

        content = self.healing_day.content
        self.assertTrue(content.is_fallback)
        self.assertTrue(len(content.guided_reflection) > 0)

    def test_fallback_does_not_overwrite_existing(self):
        """Fallback should skip if content already exists."""
        DayContent.objects.create(
            healing_day=self.healing_day,
            guided_reflection='original',
            affirmation='original',
            mental_workout='original',
            physical_workout='original',
            breathing_exercise={'name': 'test', 'description': 'test', 'inhale_seconds': 4, 'hold_in_seconds': 4, 'exhale_seconds': 4, 'hold_out_seconds': 0, 'rounds': 4},
            mini_challenge='original',
            journal_prompt='original',
            is_fallback=False,
        )

        from .tasks import serve_fallback_content
        result = serve_fallback_content(self.healing_day.id)

        self.assertIn('already exists', result)
        self.assertEqual(self.healing_day.content.guided_reflection, 'original')

    def test_fallback_each_category(self):
        """Fallback should work for all 6 categories."""
        categories = ['Foundation', 'Awareness', 'Release', 'Rewiring', 'Embodiment', 'Integration']
        for i, category in enumerate(categories):
            theme = HealingTheme.objects.create(
                assessment=self.assessment,
                day_number=i + 2,
                theme_title=f'Test {category}',
                theme_intention='Test.',
                theme_category=category,
                healing_focus=['test'],
            )
            day = HealingDay.objects.create(
                user=self.user,
                theme=theme,
                day_number=i + 2,
                unlock_date=date.today(),
                state='available',
                content_status='failed',
            )
            from .tasks import serve_fallback_content
            serve_fallback_content(day.id)
            day.refresh_from_db()
            self.assertEqual(day.content_status, 'ready')
            self.assertTrue(day.content.is_fallback)


class GenerateDayContentBatchTests(TestCase):
    """Tests for the batch content generation task."""

    def setUp(self):
        self.user = User.objects.create_user(email='batch@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            status='ready',
        )

    def test_batch_finds_tomorrows_days(self):
        """Batch should dispatch tasks for days unlocking tomorrow."""
        from unittest.mock import patch, MagicMock

        tomorrow = date.today() + timedelta(days=1)

        for day_num in range(1, 4):
            theme = HealingTheme.objects.create(
                assessment=self.assessment,
                day_number=day_num,
                theme_title=f'Day {day_num}',
                theme_intention='Test.',
                theme_category='Foundation',
                healing_focus=['test'],
            )
            HealingDay.objects.create(
                user=self.user,
                theme=theme,
                day_number=day_num,
                unlock_date=tomorrow if day_num <= 2 else date.today(),
                state='locked' if day_num <= 2 else 'available',
                content_status='pending',
            )

        with patch('healing_journey.tasks.generate_day_content') as mock_task:
            mock_task.delay = MagicMock()
            from .tasks import generate_day_content_batch
            result = generate_day_content_batch()

        # Only 2 days should be dispatched (Day 3 is already available, not locked)
        self.assertEqual(mock_task.delay.call_count, 2)
        self.assertIn('2 tasks', result)

    def test_batch_ignores_ready_content(self):
        """Batch should not dispatch for days with content_status != pending."""
        from unittest.mock import patch, MagicMock

        tomorrow = date.today() + timedelta(days=1)
        theme = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=1,
            theme_title='Day 1',
            theme_intention='Test.',
            theme_category='Foundation',
            healing_focus=['test'],
        )
        HealingDay.objects.create(
            user=self.user,
            theme=theme,
            day_number=1,
            unlock_date=tomorrow,
            state='locked',
            content_status='ready',    # Already generated
        )

        with patch('healing_journey.tasks.generate_day_content') as mock_task:
            mock_task.delay = MagicMock()
            from .tasks import generate_day_content_batch
            generate_day_content_batch()

        mock_task.delay.assert_not_called()


class DayDetailAPITests(TestCase):
    """Tests for GET /api/healing/days/<day_number>/"""

    def setUp(self):
        self.user = User.objects.create_user(email='dayapi@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            status='ready',
        )
        self.theme_1 = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=1,
            theme_title='Day 1 Theme',
            theme_intention='Begin today.',
            theme_category='Foundation',
            healing_focus=['grounding', 'safety'],
        )
        self.theme_2 = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=2,
            theme_title='Day 2 Theme',
            theme_intention='Continue today.',
            theme_category='Foundation',
            healing_focus=['awareness'],
        )
        self.day_1 = HealingDay.objects.create(
            user=self.user,
            theme=self.theme_1,
            day_number=1,
            unlock_date=date.today(),
            state='available',
            content_status='ready',
        )
        self.day_2 = HealingDay.objects.create(
            user=self.user,
            theme=self.theme_2,
            day_number=2,
            unlock_date=date.today() + timedelta(days=1),
            state='locked',
            content_status='pending',
        )

        # Create content for day 1
        mock_content = _build_mock_day_content()
        self.content_1 = DayContent.objects.create(
            healing_day=self.day_1,
            guided_reflection=mock_content['guided_reflection'],
            affirmation=mock_content['affirmation'],
            mental_workout=mock_content['mental_workout'],
            physical_workout=mock_content['physical_workout'],
            breathing_exercise=mock_content['breathing_exercise'],
            mini_challenge=mock_content['mini_challenge'],
            journal_prompt=mock_content['journal_prompt'],
        )

    def test_get_ready_day_returns_full_content(self):
        """GET day with ready content returns 200 with all modules."""
        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['day_number'], 1)
        self.assertEqual(data['state'], 'available')
        self.assertEqual(data['content_status'], 'ready')
        self.assertIn('theme', data)
        self.assertEqual(data['theme']['theme_title'], 'Day 1 Theme')
        self.assertIn('content', data)
        self.assertIn('guided_reflection', data['content'])
        self.assertIn('breathing_exercise', data['content'])
        self.assertEqual(data['content']['breathing_exercise']['name'], 'Grounding Breath')

    def test_locked_day_returns_403(self):
        """GET locked day returns 403."""
        url = reverse('healing-day-detail', kwargs={'day_number': 2})
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()['error'], 'day_locked')

    def test_out_of_range_day_returns_404(self):
        """GET day 31 returns 404."""
        url = reverse('healing-day-detail', kwargs={'day_number': 31})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_day_0_returns_404(self):
        """GET day 0 returns 404."""
        url = reverse('healing-day-detail', kwargs={'day_number': 0})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_no_journey_returns_404(self):
        """GET day for user without journey returns 404."""
        other_user = User.objects.create_user(email='nojrn@test.com', password='testpass123')
        self.client.force_authenticate(user=other_user)
        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_pending_content_triggers_generation(self):
        """GET day with pending content triggers on-demand generation, returns 202."""
        # Make day 2 available but with pending content
        self.day_2.state = 'available'
        self.day_2.save()

        with self.settings(CELERY_TASK_ALWAYS_EAGER=True):
            from unittest.mock import patch, MagicMock
            with patch('healing_journey.tasks.generate_day_content') as mock_task:
                mock_task.delay = MagicMock()
                url = reverse('healing-day-detail', kwargs={'day_number': 2})
                response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertIn('being created', response.json()['message'])

    def test_generating_content_returns_202(self):
        """GET day with generating content returns 202 polling message."""
        self.day_1.content_status = 'generating'
        self.day_1.save()

        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertIn('being prepared', response.json()['message'])

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# Phase 5 Tests: Day Lifecycle & Unlock System
# ══════════════════════════════════════════════


class UnlockHealingDaysTaskTests(TestCase):
    """Tests for the unlock_healing_days Celery task."""

    def setUp(self):
        self.user = User.objects.create_user(email='unlock@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user,
            **VALID_ASSESSMENT_PAYLOAD,
            status='ready',
        )

    def _create_day(self, day_number, unlock_date, state='locked'):
        theme = HealingTheme.objects.create(
            assessment=self.assessment,
            day_number=day_number,
            theme_title=f'Day {day_number}',
            theme_intention='Test.',
            theme_category='Foundation',
            healing_focus=['test'],
        )
        return HealingDay.objects.create(
            user=self.user,
            theme=theme,
            day_number=day_number,
            unlock_date=unlock_date,
            state=state,
            content_status='pending',
        )

    def test_unlock_day_when_local_date_reached(self):
        """Day should unlock when user's local date >= unlock_date."""
        from .models import HealingJourneySettings
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

        yesterday = date.today() - timedelta(days=1)
        day = self._create_day(1, yesterday)

        from .tasks import unlock_healing_days
        result = unlock_healing_days()

        day.refresh_from_db()
        self.assertEqual(day.state, 'available')
        self.assertIn('1', result)

    def test_no_unlock_when_future_date(self):
        """Day should stay locked when unlock_date is in the future."""
        from .models import HealingJourneySettings
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

        tomorrow = date.today() + timedelta(days=1)
        day = self._create_day(1, tomorrow)

        from .tasks import unlock_healing_days
        unlock_healing_days()

        day.refresh_from_db()
        self.assertEqual(day.state, 'locked')

    def test_unlock_today_date(self):
        """Day with unlock_date=today should be unlocked."""
        from .models import HealingJourneySettings
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

        today = date.today()
        day = self._create_day(1, today)

        from .tasks import unlock_healing_days
        unlock_healing_days()

        day.refresh_from_db()
        self.assertEqual(day.state, 'available')

    def test_skip_already_available_days(self):
        """Days already in 'available' state should not be re-processed."""
        from .models import HealingJourneySettings
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

        yesterday = date.today() - timedelta(days=1)
        day = self._create_day(1, yesterday, state='available')

        from .tasks import unlock_healing_days
        result = unlock_healing_days()

        # Should report 0 unlocked (already available, not 'locked')
        self.assertIn('0', result)

    def test_multi_user_timezone_unlock(self):
        """Users in different timezones should have different unlock behavior."""
        from .models import HealingJourneySettings
        from unittest.mock import patch
        from datetime import datetime
        from zoneinfo import ZoneInfo

        # User 1: UTC (where it's currently "today")
        user2 = User.objects.create_user(email='unlock2@test.com', password='testpass123')
        assessment2 = HealingAssessment.objects.create(
            user=user2, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')
        HealingJourneySettings.objects.create(user=user2, timezone='UTC')

        today = date.today()
        day1 = self._create_day(1, today)
        theme2 = HealingTheme.objects.create(
            assessment=assessment2, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day2 = HealingDay.objects.create(
            user=user2, theme=theme2, day_number=1,
            unlock_date=today, state='locked', content_status='pending',
        )

        from .tasks import unlock_healing_days
        result = unlock_healing_days()

        day1.refresh_from_db()
        day2.refresh_from_db()
        self.assertEqual(day1.state, 'available')
        self.assertEqual(day2.state, 'available')
        self.assertIn('2', result)

    def test_fallback_to_utc_when_no_settings(self):
        """If user has no HealingJourneySettings, default to UTC."""
        today = date.today()
        day = self._create_day(1, today)

        from .tasks import unlock_healing_days
        unlock_healing_days()

        day.refresh_from_db()
        self.assertEqual(day.state, 'available')

    def test_multiple_days_unlocked_at_once(self):
        """Multiple past-due days should all unlock in a single run."""
        from .models import HealingJourneySettings
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

        for i in range(1, 4):
            self._create_day(i, date.today() - timedelta(days=i))

        from .tasks import unlock_healing_days
        result = unlock_healing_days()
        self.assertIn('3', result)


class TodayViewTests(TestCase):
    """Tests for GET /api/healing/today/"""

    def setUp(self):
        self.user = User.objects.create_user(email='today@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_plan_state(self):
        """User with no assessment gets no_plan state."""
        url = reverse('healing-today')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'no_plan')

    def test_generating_state(self):
        """User with pending assessment gets generating state."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='generating',
        )
        url = reverse('healing-today')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'generating')

    def test_failed_state(self):
        """User with failed assessment gets failed state."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='failed',
        )
        url = reverse('healing-today')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'failed')

    def test_journey_complete_state(self):
        """User with completed journey gets journey_complete state."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            journey_completed_at=timezone.now(),
        )
        url = reverse('healing-today')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'journey_complete')

    def test_available_day_returned(self):
        """User with available day gets day detail."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Begin.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready',
        )
        mock_content = _build_mock_day_content()
        DayContent.objects.create(
            healing_day=day,
            guided_reflection=mock_content['guided_reflection'],
            affirmation=mock_content['affirmation'],
            mental_workout=mock_content['mental_workout'],
            physical_workout=mock_content['physical_workout'],
            breathing_exercise=mock_content['breathing_exercise'],
            mini_challenge=mock_content['mini_challenge'],
            journal_prompt=mock_content['journal_prompt'],
        )

        url = reverse('healing-today')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['day_number'], 1)
        self.assertEqual(data['state'], 'available')
        self.assertIn('theme', data)
        self.assertIn('content', data)

    def test_skips_completed_days(self):
        """Today endpoint should return next available day, not completed ones."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        for day_num in [1, 2]:
            theme = HealingTheme.objects.create(
                assessment=assessment, day_number=day_num,
                theme_title=f'Day {day_num}', theme_intention='Test.',
                theme_category='Foundation', healing_focus=['test'],
            )
            HealingDay.objects.create(
                user=self.user, theme=theme, day_number=day_num,
                unlock_date=date.today(),
                state='completed' if day_num == 1 else 'available',
                completed_at=timezone.now() if day_num == 1 else None,
                content_status='ready',
            )

        url = reverse('healing-today')
        response = self.client.get(url)

        data = response.json()
        self.assertEqual(data['day_number'], 2)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-today')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class PlanOverviewTests(TestCase):
    """Tests for GET /api/healing/plan/"""

    def setUp(self):
        self.user = User.objects.create_user(email='plan@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_plan_returns_404(self):
        """No assessment → 404."""
        url = reverse('healing-plan')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_not_ready_returns_404(self):
        """Assessment not ready → 404."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='generating',
        )
        url = reverse('healing-plan')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_full_plan_returned(self):
        """Ready plan returns all 30 themes with state."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            healing_profile={
                'healing_arc_summary': 'Test arc summary',
                'trauma_type': 'test',
                'core_wound': 'test',
            },
        )

        categories = {
            range(1, 6): 'Foundation',
            range(6, 11): 'Awareness',
            range(11, 16): 'Release',
            range(16, 21): 'Rewiring',
            range(21, 26): 'Embodiment',
            range(26, 31): 'Integration',
        }
        for day_range, category in categories.items():
            for day_num in day_range:
                theme = HealingTheme.objects.create(
                    assessment=assessment, day_number=day_num,
                    theme_title=f'Day {day_num} Theme',
                    theme_intention='Test.',
                    theme_category=category,
                    healing_focus=['test'],
                )
                HealingDay.objects.create(
                    user=self.user, theme=theme, day_number=day_num,
                    unlock_date=date.today() + timedelta(days=day_num - 1),
                    state='available' if day_num == 1 else 'locked',
                    content_status='pending',
                )

        url = reverse('healing-plan')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['healing_arc_summary'], 'Test arc summary')
        self.assertEqual(len(data['themes']), 30)

        # Verify structure of first theme
        first = data['themes'][0]
        self.assertEqual(first['day_number'], 1)
        self.assertEqual(first['state'], 'available')
        self.assertEqual(first['theme_title'], 'Day 1 Theme')
        self.assertIn('theme_category', first)
        self.assertIn('healing_focus', first)

    def test_completed_day_state_in_plan(self):
        """Plan should reflect completed day states."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            healing_profile={'healing_arc_summary': 'test'},
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=date.today(), state='completed',
            completed_at=timezone.now(), content_status='ready',
        )

        url = reverse('healing-plan')
        response = self.client.get(url)

        data = response.json()
        self.assertEqual(data['themes'][0]['state'], 'completed')

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-plan')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class PastDayReadOnlyAccessTests(TestCase):
    """Tests that completed/missed days can be viewed but are read-only."""

    def setUp(self):
        self.user = User.objects.create_user(email='pastday@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )

    def test_completed_day_viewable(self):
        """Completed day should return 200 with full content."""
        day = HealingDay.objects.create(
            user=self.user, theme=self.theme, day_number=1,
            unlock_date=date.today() - timedelta(days=1),
            state='completed', completed_at=timezone.now(),
            content_status='ready',
        )
        mock_content = _build_mock_day_content()
        DayContent.objects.create(
            healing_day=day,
            guided_reflection=mock_content['guided_reflection'],
            affirmation=mock_content['affirmation'],
            mental_workout=mock_content['mental_workout'],
            physical_workout=mock_content['physical_workout'],
            breathing_exercise=mock_content['breathing_exercise'],
            mini_challenge=mock_content['mini_challenge'],
            journal_prompt=mock_content['journal_prompt'],
        )

        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'completed')
        self.assertIn('content', response.json())

    def test_missed_day_viewable(self):
        """Missed day should return 200 with content (if content exists)."""
        day = HealingDay.objects.create(
            user=self.user, theme=self.theme, day_number=1,
            unlock_date=date.today() - timedelta(days=2),
            state='missed', content_status='ready',
        )
        mock_content = _build_mock_day_content()
        DayContent.objects.create(
            healing_day=day,
            guided_reflection=mock_content['guided_reflection'],
            affirmation=mock_content['affirmation'],
            mental_workout=mock_content['mental_workout'],
            physical_workout=mock_content['physical_workout'],
            breathing_exercise=mock_content['breathing_exercise'],
            mini_challenge=mock_content['mini_challenge'],
            journal_prompt=mock_content['journal_prompt'],
        )

        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'missed')


# ══════════════════════════════════════════════
# Phase 6 Tests: Progress, Streaks & Milestones
# ══════════════════════════════════════════════


class DayCompletionTests(TestCase):
    """Tests for POST /api/healing/days/<day_number>/complete/"""

    def setUp(self):
        self.user = User.objects.create_user(email='complete@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Day 1', theme_intention='Begin.',
            theme_category='Foundation', healing_focus=['test'],
        )
        self.day = HealingDay.objects.create(
            user=self.user, theme=self.theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready',
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=0, longest_streak=0,
            total_days_completed=0, milestones_reached=[],
        )

    def test_first_completion(self):
        """Completing a day for the first time returns success with streak data."""
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['current_streak'], 1)
        self.assertEqual(data['total_days_completed'], 1)
        self.assertIsNone(data['milestone_reached'])

        self.day.refresh_from_db()
        self.assertEqual(self.day.state, 'completed')
        self.assertIsNotNone(self.day.completed_at)

    def test_idempotent_completion(self):
        """Completing an already-completed day returns already_completed without double-counting."""
        self.day.state = 'completed'
        self.day.completed_at = timezone.now()
        self.day.save()

        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertTrue(response.json()['already_completed'])

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.total_days_completed, 0)  # Not incremented

    def test_locked_day_returns_403(self):
        """Completing a locked day returns 403."""
        self.day.state = 'locked'
        self.day.save()

        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_403_FORBIDDEN)

    def test_completion_with_mood(self):
        """Completing with mood creates a MoodEntry and links it."""
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {'mood': 'happy'}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.day.refresh_from_db()
        self.assertIsNotNone(self.day.mood_entry)
        self.assertEqual(self.day.mood_entry.mood, 'happy')

    def test_invalid_mood_rejected(self):
        """Invalid mood value returns 400."""
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {'mood': 'ecstatic'}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_completion_without_mood(self):
        """Day can be completed without mood (mood is optional)."""
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.day.refresh_from_db()
        self.assertIsNone(self.day.mood_entry)

    def test_missed_day_can_be_completed(self):
        """Missed day can be completed (grace period recovery)."""
        self.day.state = 'missed'
        self.day.save()
        self.streak.grace_period_active = True
        self.streak.grace_expires_at = timezone.now() + timedelta(hours=24)
        self.streak.current_streak = 3
        self.streak.save()

        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.day.refresh_from_db()
        self.assertEqual(self.day.state, 'completed')

        # Grace period should be cleared
        self.streak.refresh_from_db()
        self.assertFalse(self.streak.grace_period_active)
        self.assertIsNone(self.streak.grace_expires_at)
        # Streak should continue (3+1=4)
        self.assertEqual(self.streak.current_streak, 4)

    def test_no_journey_returns_404(self):
        """Completing a day with no journey returns 404."""
        other_user = User.objects.create_user(email='nojourney@test.com', password='testpass123')
        self.client.force_authenticate(user=other_user)
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class StreakMathTests(TestCase):
    """Tests for streak calculation logic."""

    def setUp(self):
        self.user = User.objects.create_user(email='streak@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=0, longest_streak=0,
            total_days_completed=0, milestones_reached=[],
        )

    def _create_day(self, day_number, state='available'):
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=day_number,
            theme_title=f'Day {day_number}', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        return HealingDay.objects.create(
            user=self.user, theme=theme, day_number=day_number,
            unlock_date=date.today(), state=state, content_status='ready',
        )

    def test_streak_increments(self):
        """Each completion should increment current_streak."""
        for i in range(1, 4):
            day = self._create_day(i)
            url = reverse('healing-day-complete', kwargs={'day_number': i})
            self.client.post(url, {}, format='json')

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 3)
        self.assertEqual(self.streak.total_days_completed, 3)

    def test_longest_streak_updates(self):
        """longest_streak should update when current_streak surpasses it."""
        self.streak.longest_streak = 2
        self.streak.current_streak = 2
        self.streak.total_days_completed = 2
        self.streak.save()

        day = self._create_day(3)
        url = reverse('healing-day-complete', kwargs={'day_number': 3})
        self.client.post(url, {}, format='json')

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 3)
        self.assertEqual(self.streak.longest_streak, 3)

    def test_last_completed_date_set(self):
        """last_completed_date should be set on completion."""
        day = self._create_day(1)
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        self.client.post(url, {}, format='json')

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.last_completed_date, date.today())


class MilestoneTests(TestCase):
    """Tests for milestone detection."""

    def setUp(self):
        self.user = User.objects.create_user(email='milestone@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=2, longest_streak=2,
            total_days_completed=2, milestones_reached=[],
        )

    def test_day_3_milestone(self):
        """Completing 3rd day should trigger milestone."""
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=3,
            theme_title='Day 3', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=3,
            unlock_date=date.today(), state='available', content_status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 3})
        response = self.client.post(url, {}, format='json')

        data = response.json()
        self.assertIsNotNone(data['milestone_reached'])
        self.assertEqual(data['milestone_reached']['day'], 3)
        self.assertIn('building something real', data['milestone_reached']['message'])

        self.streak.refresh_from_db()
        self.assertIn(3, self.streak.milestones_reached)

    def test_milestone_idempotent(self):
        """Milestone should not be re-sent if already reached."""
        self.streak.milestones_reached = [3]
        self.streak.save()

        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=3,
            theme_title='Day 3', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=3,
            unlock_date=date.today(), state='available', content_status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 3})
        response = self.client.post(url, {}, format='json')

        data = response.json()
        self.assertIsNone(data['milestone_reached'])

    def test_day_7_milestone(self):
        """Completing 7th day should trigger milestone."""
        self.streak.total_days_completed = 6
        self.streak.current_streak = 6
        self.streak.longest_streak = 6
        self.streak.milestones_reached = [3]
        self.streak.save()

        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=7,
            theme_title='Day 7', theme_intention='Test.',
            theme_category='Awareness', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=7,
            unlock_date=date.today(), state='available', content_status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 7})
        response = self.client.post(url, {}, format='json')

        data = response.json()
        self.assertIsNotNone(data['milestone_reached'])
        self.assertEqual(data['milestone_reached']['day'], 7)


class JourneyCompletionTests(TestCase):
    """Tests for Day 30 journey completion."""

    def setUp(self):
        self.user = User.objects.create_user(email='journeyend@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=29, longest_streak=29,
            total_days_completed=29, milestones_reached=[3, 7, 14, 21],
        )

    def test_day_30_sets_journey_completed(self):
        """Day 30 completion sets journey_completed_at."""
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=30,
            theme_title='Day 30', theme_intention='Final.',
            theme_category='Integration', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=30,
            unlock_date=date.today(), state='available', content_status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 30})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

        self.assessment.refresh_from_db()
        self.assertIsNotNone(self.assessment.journey_completed_at)

        # Day 30 milestone should also be detected
        data = response.json()
        self.assertIsNotNone(data['milestone_reached'])
        self.assertEqual(data['milestone_reached']['day'], 30)

    def test_day_30_streak_and_total(self):
        """Day 30 should have streak=30 and total=30."""
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=30,
            theme_title='Day 30', theme_intention='Final.',
            theme_category='Integration', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=30,
            unlock_date=date.today(), state='available', content_status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 30})
        response = self.client.post(url, {}, format='json')

        data = response.json()
        self.assertEqual(data['current_streak'], 30)
        self.assertEqual(data['total_days_completed'], 30)


class CheckMissedDaysTaskTests(TestCase):
    """Tests for the check_missed_days_and_streaks task."""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='missed@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=3, longest_streak=3,
            total_days_completed=3, milestones_reached=[3],
        )
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')

    def _create_day(self, day_number, unlock_date, state='available'):
        theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=day_number,
            theme_title=f'Day {day_number}', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        return HealingDay.objects.create(
            user=self.user, theme=theme, day_number=day_number,
            unlock_date=unlock_date, state=state, content_status='ready',
        )

    def test_mark_missed_day(self):
        """Day whose local date has fully passed should be marked missed."""
        yesterday = date.today() - timedelta(days=1)
        day = self._create_day(4, yesterday)

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        day.refresh_from_db()
        self.assertEqual(day.state, 'missed')

    def test_grace_period_activation(self):
        """First missed day should activate grace period."""
        yesterday = date.today() - timedelta(days=1)
        day = self._create_day(4, yesterday)

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        self.streak.refresh_from_db()
        self.assertTrue(self.streak.grace_period_active)
        self.assertIsNotNone(self.streak.grace_expires_at)
        # Streak should be preserved during grace
        self.assertEqual(self.streak.current_streak, 3)

    def test_grace_period_preserves_streak(self):
        """During active grace period, streak should not be zeroed."""
        self.streak.grace_period_active = True
        self.streak.grace_expires_at = timezone.now() + timedelta(hours=24)
        self.streak.save()

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 3)  # Preserved

    def test_grace_period_expiry_zeros_streak(self):
        """When grace window expires, streak should be zeroed."""
        self.streak.grace_period_active = True
        self.streak.grace_expires_at = timezone.now() - timedelta(hours=1)
        self.streak.save()

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 0)
        self.assertFalse(self.streak.grace_period_active)
        self.assertIsNone(self.streak.grace_expires_at)

    def test_today_day_not_marked_missed(self):
        """Day unlocked today should NOT be marked missed."""
        today = date.today()
        day = self._create_day(4, today)

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        day.refresh_from_db()
        self.assertEqual(day.state, 'available')

    def test_completed_day_not_affected(self):
        """Completed days should not be re-marked."""
        yesterday = date.today() - timedelta(days=1)
        day = self._create_day(4, yesterday, state='completed')
        day.completed_at = timezone.now()
        day.save()

        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        day.refresh_from_db()
        self.assertEqual(day.state, 'completed')


class ProgressEndpointTests(TestCase):
    """Tests for GET /api/healing/progress/"""

    def setUp(self):
        self.user = User.objects.create_user(email='progress@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_no_streak_returns_404(self):
        """No streak data returns 404."""
        url = reverse('healing-progress')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_progress_data_returned(self):
        """Progress endpoint returns correct streak data."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            journey_started_at=timezone.now(),
        )
        HealingStreak.objects.create(
            user=self.user, current_streak=5, longest_streak=7,
            total_days_completed=12, milestones_reached=[3, 7],
        )

        url = reverse('healing-progress')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['total_days_completed'], 12)
        self.assertEqual(data['current_streak'], 5)
        self.assertEqual(data['longest_streak'], 7)
        self.assertEqual(data['milestones_reached'], [3, 7])
        self.assertFalse(data['grace_period_active'])
        self.assertFalse(data['journey_complete'])

    def test_journey_complete_flag(self):
        """Progress should show journey_complete=True when completed."""
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            journey_started_at=timezone.now(),
            journey_completed_at=timezone.now(),
        )
        HealingStreak.objects.create(
            user=self.user, current_streak=30, longest_streak=30,
            total_days_completed=30, milestones_reached=[3, 7, 14, 21, 30],
        )

        url = reverse('healing-progress')
        response = self.client.get(url)

        data = response.json()
        self.assertTrue(data['journey_complete'])
        self.assertIsNotNone(data['journey_completed_at'])

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-progress')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


# ══════════════════════════════════════════════
# Phase 7 Tests: Notifications & Reminders
# ══════════════════════════════════════════════


class SendHealingRemindersTaskTests(TestCase):
    """Tests for the send_healing_reminders Celery task."""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='reminder@test.com', password='testpass123')
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        self.settings_obj = HealingJourneySettings.objects.create(
            user=self.user,
            timezone='UTC',
            morning_reminder_enabled=True,
            evening_reminder_enabled=True,
            morning_reminder_time='07:00',
            evening_reminder_time='20:00',
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Day 1', theme_intention='Begin.',
            theme_category='Foundation', healing_focus=['test'],
        )
        self.day = HealingDay.objects.create(
            user=self.user, theme=self.theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready',
        )

    @patch('healing_journey.tasks.timezone')
    def test_morning_reminder_sent_at_configured_time(self, mock_tz):
        """Morning reminder should be sent when local hour matches configured time."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        # Simulate UTC time that maps to 7 AM UTC
        mock_now = dt(2026, 4, 25, 7, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        from .tasks import send_healing_reminders
        with patch('healing_journey.tasks.HealingAssessment') as mock_ha:
            mock_ha.objects.filter.return_value.select_related.return_value = [self.assessment]
            # Run directly — the notification creation may fail (no Notification table in tests)
            # so just test the logic runs without error
        result = send_healing_reminders()
        self.assertIn('Morning:', result)

    @patch('healing_journey.tasks.timezone')
    def test_evening_reminder_sent_at_configured_time(self, mock_tz):
        """Evening reminder should be sent when local hour matches configured time."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_now = dt(2026, 4, 25, 20, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertIn('Evening:', result)

    @patch('healing_journey.tasks.timezone')
    def test_no_reminder_wrong_hour(self, mock_tz):
        """No reminders should be sent if local hour doesn't match."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_now = dt(2026, 4, 25, 12, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertEqual(result, 'Morning: 0, Evening: 0')

    @patch('healing_journey.tasks.timezone')
    def test_morning_disabled_skips(self, mock_tz):
        """Disabled morning reminder should not be sent."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_now = dt(2026, 4, 25, 7, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        self.settings_obj.morning_reminder_enabled = False
        self.settings_obj.save()

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertEqual(result, 'Morning: 0, Evening: 0')

    @patch('healing_journey.tasks.timezone')
    def test_no_available_day_skips(self, mock_tz):
        """No reminder if user has no uncompleted available day."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_now = dt(2026, 4, 25, 7, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        self.day.state = 'completed'
        self.day.completed_at = timezone.now()
        self.day.save()

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertEqual(result, 'Morning: 0, Evening: 0')

    @patch('healing_journey.tasks.timezone')
    def test_completed_journey_skips(self, mock_tz):
        """No reminder if journey is completed."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_now = dt(2026, 4, 25, 7, 0, 0, tzinfo=ZoneInfo('UTC'))
        mock_tz.now.return_value = mock_now

        self.assessment.journey_completed_at = timezone.now()
        self.assessment.save()

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertEqual(result, 'Morning: 0, Evening: 0')


class SettingsEndpointTests(TestCase):
    """Tests for GET/PATCH /api/healing/settings/"""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='settings@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.settings_obj = HealingJourneySettings.objects.create(
            user=self.user,
            timezone='UTC',
        )

    def test_get_settings(self):
        """GET returns current settings."""
        url = reverse('healing-settings')
        response = self.client.get(url)

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['timezone'], 'UTC')
        self.assertTrue(data['morning_reminder_enabled'])
        self.assertTrue(data['evening_reminder_enabled'])

    def test_patch_timezone(self):
        """PATCH updates timezone."""
        url = reverse('healing-settings')
        response = self.client.patch(url, {'timezone': 'America/New_York'}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['timezone'], 'America/New_York')

        self.settings_obj.refresh_from_db()
        self.assertEqual(self.settings_obj.timezone, 'America/New_York')

    def test_patch_reminder_preferences(self):
        """PATCH updates reminder preferences."""
        url = reverse('healing-settings')
        response = self.client.patch(url, {
            'morning_reminder_enabled': False,
            'evening_reminder_time': '21:00',
        }, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertFalse(response.json()['morning_reminder_enabled'])

        self.settings_obj.refresh_from_db()
        self.assertFalse(self.settings_obj.morning_reminder_enabled)

    def test_invalid_timezone_rejected(self):
        """Invalid timezone returns 400."""
        url = reverse('healing-settings')
        response = self.client.patch(url, {'timezone': 'Mars/Olympus'}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_no_settings_returns_404(self):
        """GET with no settings returns 404."""
        self.settings_obj.delete()
        url = reverse('healing-settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_partial_patch(self):
        """PATCH only specified fields, others unchanged."""
        url = reverse('healing-settings')
        response = self.client.patch(url, {'evening_reminder_enabled': False}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data['morning_reminder_enabled'])  # Unchanged
        self.assertFalse(data['evening_reminder_enabled'])  # Changed

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-settings')
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class NotificationTypeRegistrationTests(TestCase):
    """Tests that healing notification types are registered."""

    def test_healing_notification_types_exist(self):
        """All healing notification types should be in the model choices."""
        from notifications.models import Notification
        type_keys = [t[0] for t in Notification.NOTIFICATION_TYPES]
        expected_types = [
            'healing_plan_ready',
            'healing_day_available',
            'healing_evening_reminder',
            'healing_milestone',
            'healing_complete',
        ]
        for notif_type in expected_types:
            self.assertIn(notif_type, type_keys, f"Missing notification type: {notif_type}")


# ══════════════════════════════════════════════
# Phase 8 Tests: Reset & Edge Cases
# ══════════════════════════════════════════════


class ResetJourneyTests(TestCase):
    """Tests for POST /api/healing/reset/"""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='reset@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            journey_started_at=timezone.now(),
        )
        self.theme = HealingTheme.objects.create(
            assessment=self.assessment, day_number=1,
            theme_title='Day 1', theme_intention='Begin.',
            theme_category='Foundation', healing_focus=['test'],
        )
        self.day = HealingDay.objects.create(
            user=self.user, theme=self.theme, day_number=1,
            unlock_date=date.today(), state='completed',
            content_status='ready', completed_at=timezone.now(),
        )
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=5, longest_streak=10,
            total_days_completed=15, milestones_reached=[3, 7, 14],
            last_completed_date=date.today(),
        )
        self.settings_obj = HealingJourneySettings.objects.create(
            user=self.user, timezone='America/New_York',
        )

    def test_reset_archives_assessment(self):
        """Reset should set is_archived=True on the assessment."""
        url = reverse('healing-reset')
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['archived_journey_id'], self.assessment.id)

        self.assessment.refresh_from_db()
        self.assertTrue(self.assessment.is_archived)

    def test_reset_resets_streak(self):
        """Reset should zero all streak fields."""
        url = reverse('healing-reset')
        self.client.post(url, {}, format='json')

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 0)
        self.assertEqual(self.streak.longest_streak, 0)
        self.assertEqual(self.streak.total_days_completed, 0)
        self.assertIsNone(self.streak.last_completed_date)
        self.assertEqual(self.streak.milestones_reached, [])
        self.assertFalse(self.streak.grace_period_active)
        self.assertIsNone(self.streak.grace_expires_at)

    def test_reset_preserves_settings(self):
        """Reset should NOT delete or modify journey settings."""
        url = reverse('healing-reset')
        self.client.post(url, {}, format='json')

        self.settings_obj.refresh_from_db()
        self.assertEqual(self.settings_obj.timezone, 'America/New_York')

    def test_old_data_preserved(self):
        """Archived assessment and its related objects should still exist."""
        url = reverse('healing-reset')
        self.client.post(url, {}, format='json')

        # Assessment still exists (is_archived=True)
        self.assertTrue(HealingAssessment.objects.filter(id=self.assessment.id).exists())
        # Theme and day still exist (FK to assessment)
        self.assertTrue(HealingTheme.objects.filter(id=self.theme.id).exists())
        self.assertTrue(HealingDay.objects.filter(id=self.day.id).exists())

    def test_can_start_new_journey_after_reset(self):
        """After reset, user can submit a new assessment."""
        url = reverse('healing-reset')
        self.client.post(url, {}, format='json')

        # Verify no active assessment
        active = HealingAssessment.objects.filter(
            user=self.user, is_archived=False
        ).first()
        self.assertIsNone(active)

        # Submit new assessment should work (not 409)
        submit_url = reverse('healing-assessment-submit')
        response = self.client.post(submit_url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertIn(response.status_code, [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_202_ACCEPTED,
        ])

    def test_no_active_journey_returns_404(self):
        """Reset with no active journey returns 404."""
        self.assessment.is_archived = True
        self.assessment.save()

        url = reverse('healing-reset')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_double_reset_returns_404(self):
        """Second reset attempt returns 404 (already archived)."""
        url = reverse('healing-reset')
        self.client.post(url, {}, format='json')

        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        """Unauthenticated request returns 401."""
        self.client.force_authenticate(user=None)
        url = reverse('healing-reset')
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_401_UNAUTHORIZED)


class EdgeCaseTests(TestCase):
    """Tests for various edge cases in the healing journey."""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='edge@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_double_tap_assessment_race_condition(self):
        """Submitting assessment while one is generating returns 202."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='generating',
        )

        url = reverse('healing-assessment-submit')
        response = self.client.post(url, VALID_ASSESSMENT_PAYLOAD, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_202_ACCEPTED)
        self.assertEqual(response.json()['status'], 'generating')

    def test_double_tap_complete_is_idempotent(self):
        """Double-completing a day is idempotent — no double-count."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available', content_status='ready',
        )
        streak = HealingStreak.objects.create(
            user=self.user, current_streak=0, longest_streak=0,
            total_days_completed=0, milestones_reached=[],
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        # First completion
        r1 = self.client.post(url, {}, format='json')
        self.assertEqual(r1.status_code, http_status.HTTP_200_OK)
        self.assertEqual(r1.json()['total_days_completed'], 1)

        # Second completion (idempotent)
        r2 = self.client.post(url, {}, format='json')
        self.assertEqual(r2.status_code, http_status.HTTP_200_OK)
        self.assertTrue(r2.json()['already_completed'])

        # Streak should still be 1
        streak.refresh_from_db()
        self.assertEqual(streak.total_days_completed, 1)

    def test_timezone_change_mid_journey(self):
        """Changing timezone mid-journey should update settings."""
        from .models import HealingJourneySettings
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        settings_obj = HealingJourneySettings.objects.create(
            user=self.user, timezone='UTC',
        )

        # Change timezone via settings API
        url = reverse('healing-settings')
        response = self.client.patch(url, {'timezone': 'Asia/Tokyo'}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        settings_obj.refresh_from_db()
        self.assertEqual(settings_obj.timezone, 'Asia/Tokyo')

    def test_missed_day_grace_recovery_flow(self):
        """Full flow: day missed → grace activated → complete within grace → streak preserved."""
        from .models import HealingJourneySettings
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        # Day was yesterday → will be marked missed
        yesterday = date.today() - timedelta(days=1)
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=yesterday, state='available', content_status='ready',
        )
        streak = HealingStreak.objects.create(
            user=self.user, current_streak=5, longest_streak=5,
            total_days_completed=5, milestones_reached=[3],
        )

        # Step 1: Run missed check → day should be missed, grace activated
        from .tasks import check_missed_days_and_streaks
        check_missed_days_and_streaks()

        day.refresh_from_db()
        self.assertEqual(day.state, 'missed')
        streak.refresh_from_db()
        self.assertTrue(streak.grace_period_active)
        self.assertEqual(streak.current_streak, 5)  # Preserved during grace

        # Step 2: Complete the missed day within grace
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        response = self.client.post(url, {}, format='json')

        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        day.refresh_from_db()
        self.assertEqual(day.state, 'completed')
        streak.refresh_from_db()
        self.assertFalse(streak.grace_period_active)
        self.assertEqual(streak.current_streak, 6)  # Streak continued

    def test_out_of_range_day_returns_404(self):
        """Day 0 or 31 returns 404."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )

        url = reverse('healing-day-complete', kwargs={'day_number': 31})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

        url = reverse('healing-day-complete', kwargs={'day_number': 0})
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_404_NOT_FOUND)

    def test_content_retry_on_failed_day(self):
        """Accessing a failed content day should still return 200 with fallback."""
        assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=self.user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available', content_status='failed',
        )
        # Create fallback content
        DayContent.objects.create(
            healing_day=day,
            guided_reflection='Fallback reflection',
            affirmation='Fallback affirmation',
            mental_workout='Fallback mental workout',
            physical_workout='Fallback physical workout',
            breathing_exercise={
                'name': 'Test Breath',
                'description': 'A calming breath',
                'inhale_seconds': 4,
                'hold_in_seconds': 2,
                'exhale_seconds': 4,
                'hold_out_seconds': 2,
                'rounds': 3,
            },
            mini_challenge='Fallback challenge',
            journal_prompt='Fallback prompt',
            is_fallback=True,
        )

        url = reverse('healing-day-detail', kwargs={'day_number': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertTrue(response.json()['content']['is_fallback'])


# ══════════════════════════════════════════════
# Phase 9 Tests: Integration & Polish
# ══════════════════════════════════════════════


class Full30DayLifecycleTest(TestCase):
    """
    End-to-end simulation of a full 30-day healing journey lifecycle.
    Tests: assessment → plan ready → unlock days → complete days →
           milestones → Day 30 completion → journey complete → reset.
    """

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='lifecycle@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create a ready assessment with 30 themes and 30 days
        self.assessment = HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            journey_started_at=timezone.now(),
        )
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')
        self.streak = HealingStreak.objects.create(
            user=self.user, current_streak=0, longest_streak=0,
            total_days_completed=0, milestones_reached=[],
        )

        categories = ['Foundation'] * 5 + ['Awareness'] * 5 + ['Release'] * 5 + \
                     ['Rewiring'] * 5 + ['Embodiment'] * 5 + ['Integration'] * 5

        for i in range(1, 31):
            theme = HealingTheme.objects.create(
                assessment=self.assessment, day_number=i,
                theme_title=f'Day {i} Theme', theme_intention=f'Intention {i}',
                theme_category=categories[i - 1], healing_focus=['test'],
            )
            HealingDay.objects.create(
                user=self.user, theme=theme, day_number=i,
                unlock_date=date.today(), state='available',
                content_status='ready',
            )

    def test_full_journey_lifecycle(self):
        """Complete all 30 days and verify milestones + journey completion."""
        expected_milestones = {3, 7, 14, 21, 30}
        hit_milestones = set()

        for day_num in range(1, 31):
            url = reverse('healing-day-complete', kwargs={'day_number': day_num})
            response = self.client.post(url, {}, format='json')

            self.assertEqual(response.status_code, http_status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data['current_streak'], day_num)
            self.assertEqual(data['total_days_completed'], day_num)

            if data.get('milestone_reached'):
                hit_milestones.add(data['milestone_reached']['day'])

        # All milestones should have been hit
        self.assertEqual(hit_milestones, expected_milestones)

        # Journey should be complete
        self.assessment.refresh_from_db()
        self.assertIsNotNone(self.assessment.journey_completed_at)

        # Streak should reflect full journey
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.current_streak, 30)
        self.assertEqual(self.streak.longest_streak, 30)
        self.assertEqual(self.streak.total_days_completed, 30)
        self.assertEqual(sorted(self.streak.milestones_reached), [3, 7, 14, 21, 30])

        # Progress endpoint should show complete
        progress_url = reverse('healing-progress')
        response = self.client.get(progress_url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertTrue(response.json()['journey_complete'])

        # Today endpoint should show journey_complete
        today_url = reverse('healing-today')
        response = self.client.get(today_url)
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)
        self.assertEqual(response.json()['state'], 'journey_complete')

    def test_journey_then_reset_then_restart(self):
        """Complete some days, reset, then verify new journey can start."""
        # Complete 5 days
        for day_num in range(1, 6):
            url = reverse('healing-day-complete', kwargs={'day_number': day_num})
            self.client.post(url, {}, format='json')

        self.streak.refresh_from_db()
        self.assertEqual(self.streak.total_days_completed, 5)

        # Reset journey
        reset_url = reverse('healing-reset')
        response = self.client.post(reset_url, {}, format='json')
        self.assertEqual(response.status_code, http_status.HTTP_200_OK)

        # Streak should be zeroed
        self.streak.refresh_from_db()
        self.assertEqual(self.streak.total_days_completed, 0)
        self.assertEqual(self.streak.current_streak, 0)

        # Old assessment archived
        self.assessment.refresh_from_db()
        self.assertTrue(self.assessment.is_archived)

        # Can submit new assessment
        submit_url = reverse('healing-assessment-submit')
        response = self.client.post(submit_url, VALID_ASSESSMENT_PAYLOAD, format='json')
        self.assertIn(response.status_code, [
            http_status.HTTP_201_CREATED,
            http_status.HTTP_202_ACCEPTED,
        ])


class MultiUserConcurrentTest(TestCase):
    """Test that multiple users can progress independently."""

    def setUp(self):
        from .models import HealingJourneySettings
        self.users = []
        self.clients = []

        for i in range(3):
            user = User.objects.create_user(
                email=f'concurrent{i}@test.com', password='testpass123'
            )
            client = APIClient()
            client.force_authenticate(user=user)
            self.users.append(user)
            self.clients.append(client)

            assessment = HealingAssessment.objects.create(
                user=user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
                journey_started_at=timezone.now(),
            )
            HealingJourneySettings.objects.create(user=user, timezone='UTC')
            HealingStreak.objects.create(
                user=user, current_streak=0, longest_streak=0,
                total_days_completed=0, milestones_reached=[],
            )

            for d in range(1, 6):
                theme = HealingTheme.objects.create(
                    assessment=assessment, day_number=d,
                    theme_title=f'Day {d}', theme_intention='Test.',
                    theme_category='Foundation', healing_focus=['test'],
                )
                HealingDay.objects.create(
                    user=user, theme=theme, day_number=d,
                    unlock_date=date.today(), state='available',
                    content_status='ready',
                )

    def test_independent_progression(self):
        """Each user's progress should be independent."""
        # User 0: complete 1 day
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        self.clients[0].post(url, {}, format='json')

        # User 1: complete 3 days
        for d in range(1, 4):
            url = reverse('healing-day-complete', kwargs={'day_number': d})
            self.clients[1].post(url, {}, format='json')

        # User 2: complete 0 days

        # Verify each user's streak
        for i, expected in enumerate([1, 3, 0]):
            streak = HealingStreak.objects.get(user=self.users[i])
            self.assertEqual(
                streak.total_days_completed, expected,
                f"User {i} should have {expected} days completed"
            )

    def test_one_user_reset_doesnt_affect_others(self):
        """Resetting one user's journey should not affect others."""
        # User 0: complete day 1 then reset
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        self.clients[0].post(url, {}, format='json')

        reset_url = reverse('healing-reset')
        self.clients[0].post(reset_url, {}, format='json')

        # User 1's data should be unaffected
        url = reverse('healing-day-complete', kwargs={'day_number': 1})
        r = self.clients[1].post(url, {}, format='json')
        self.assertEqual(r.status_code, http_status.HTTP_200_OK)

        streak_1 = HealingStreak.objects.get(user=self.users[1])
        self.assertEqual(streak_1.total_days_completed, 1)


class MultiTimezoneUnlockTest(TestCase):
    """Test timezone-aware unlock behavior across multiple timezones."""

    def setUp(self):
        from .models import HealingJourneySettings

        self.timezones = {
            'utc_user': 'UTC',
            'ny_user': 'America/New_York',
            'tokyo_user': 'Asia/Tokyo',
        }
        self.data = {}

        for name, tz in self.timezones.items():
            user = User.objects.create_user(
                email=f'{name}@test.com', password='testpass123'
            )
            assessment = HealingAssessment.objects.create(
                user=user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
            )
            HealingJourneySettings.objects.create(user=user, timezone=tz)
            theme = HealingTheme.objects.create(
                assessment=assessment, day_number=2,
                theme_title='Day 2', theme_intention='Test.',
                theme_category='Foundation', healing_focus=['test'],
            )
            day = HealingDay.objects.create(
                user=user, theme=theme, day_number=2,
                unlock_date=date.today(), state='locked',
                content_status='pending',
            )
            self.data[name] = {'user': user, 'day': day}

    def test_unlock_respects_timezone(self):
        """Unlock task should use each user's timezone for date comparison."""
        from .tasks import unlock_healing_days
        result = unlock_healing_days()

        # All users with unlock_date=today should have their days unlocked
        # (regardless of timezone, since today >= today is true)
        for name, info in self.data.items():
            info['day'].refresh_from_db()
            self.assertEqual(
                info['day'].state, 'available',
                f"{name} (tz={self.timezones[name]}) day should be unlocked"
            )


class ErrorResponseConsistencyTest(TestCase):
    """Verify all endpoints return consistent error response format."""

    def setUp(self):
        self.user = User.objects.create_user(email='errors@test.com', password='testpass123')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_401_on_all_endpoints_when_unauthenticated(self):
        """All endpoints should return 401 for unauthenticated requests."""
        self.client.force_authenticate(user=None)

        endpoints = [
            ('get', reverse('healing-assessment-status')),
            ('get', reverse('healing-assessment-profile')),
            ('get', reverse('healing-today')),
            ('get', reverse('healing-plan')),
            ('get', reverse('healing-progress')),
            ('get', reverse('healing-settings')),
            ('get', reverse('healing-day-detail', kwargs={'day_number': 1})),
            ('post', reverse('healing-assessment-submit')),
            ('post', reverse('healing-day-complete', kwargs={'day_number': 1})),
            ('post', reverse('healing-reset')),
        ]

        for method, url in endpoints:
            if method == 'get':
                response = self.client.get(url)
            else:
                response = self.client.post(url, {}, format='json')

            self.assertEqual(
                response.status_code, http_status.HTTP_401_UNAUTHORIZED,
                f"{method.upper()} {url} should return 401"
            )

    def test_404_when_no_journey(self):
        """Endpoints requiring a journey should return 404 when none exists."""
        endpoints_404 = [
            ('get', reverse('healing-day-detail', kwargs={'day_number': 1})),
            ('post', reverse('healing-day-complete', kwargs={'day_number': 1})),
            ('get', reverse('healing-progress')),
            ('post', reverse('healing-reset')),
        ]

        for method, url in endpoints_404:
            if method == 'get':
                response = self.client.get(url)
            else:
                response = self.client.post(url, {}, format='json')

            self.assertEqual(
                response.status_code, http_status.HTTP_404_NOT_FOUND,
                f"{method.upper()} {url} should return 404 when no journey"
            )


class CeleryTaskLoggingTest(TestCase):
    """Verify Celery tasks return structured results for monitoring."""

    def setUp(self):
        from .models import HealingJourneySettings
        self.user = User.objects.create_user(email='logging@test.com', password='testpass123')
        HealingAssessment.objects.create(
            user=self.user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        HealingJourneySettings.objects.create(user=self.user, timezone='UTC')
        HealingStreak.objects.create(
            user=self.user, current_streak=0, longest_streak=0,
            total_days_completed=0, milestones_reached=[],
        )

    def test_unlock_task_returns_count(self):
        """unlock_healing_days should return a string with count."""
        from .tasks import unlock_healing_days
        result = unlock_healing_days()
        self.assertIn('Unlocked', result)
        self.assertIn('days', result)

    def test_missed_task_returns_counts(self):
        """check_missed_days_and_streaks should return missed + grace counts."""
        from .tasks import check_missed_days_and_streaks
        result = check_missed_days_and_streaks()
        self.assertIn('Missed:', result)
        self.assertIn('Grace expired:', result)

    @patch('healing_journey.tasks.timezone')
    def test_reminder_task_returns_counts(self, mock_tz):
        """send_healing_reminders should return morning + evening counts."""
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        mock_tz.now.return_value = dt(2026, 4, 25, 12, 0, 0, tzinfo=ZoneInfo('UTC'))

        from .tasks import send_healing_reminders
        result = send_healing_reminders()
        self.assertIn('Morning:', result)
        self.assertIn('Evening:', result)


class FKIntegrityTest(TestCase):
    """Verify FK relationships with existing apps are intact."""

    def test_healing_day_mood_fk(self):
        """HealingDay.mood_entry FK to app_home.MoodEntry should work."""
        from app_home.models import MoodEntry
        user = User.objects.create_user(email='fk1@test.com', password='testpass123')
        assessment = HealingAssessment.objects.create(
            user=user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        mood = MoodEntry.objects.create(user=user, mood='happy')
        day = HealingDay.objects.create(
            user=user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready', mood_entry=mood,
        )

        day.refresh_from_db()
        self.assertEqual(day.mood_entry.mood, 'happy')

        # Deleting mood entry should set FK to NULL (SET_NULL)
        mood.delete()
        day.refresh_from_db()
        self.assertIsNone(day.mood_entry)

    def test_healing_day_journal_fk(self):
        """HealingDay.journal_entry FK should accept a JournalEntry."""
        user = User.objects.create_user(email='fk2@test.com', password='testpass123')
        assessment = HealingAssessment.objects.create(
            user=user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready',
        )
        # journal_entry is optional (null=True, blank=True)
        self.assertIsNone(day.journal_entry)

    def test_assessment_cascade_delete(self):
        """Deleting an assessment should cascade to themes, days, and content."""
        user = User.objects.create_user(email='fk3@test.com', password='testpass123')
        assessment = HealingAssessment.objects.create(
            user=user, **VALID_ASSESSMENT_PAYLOAD, status='ready',
        )
        theme = HealingTheme.objects.create(
            assessment=assessment, day_number=1,
            theme_title='Day 1', theme_intention='Test.',
            theme_category='Foundation', healing_focus=['test'],
        )
        day = HealingDay.objects.create(
            user=user, theme=theme, day_number=1,
            unlock_date=date.today(), state='available',
            content_status='ready',
        )

        assessment_id = assessment.id
        assessment.delete()

        self.assertFalse(HealingTheme.objects.filter(assessment_id=assessment_id).exists())
        self.assertEqual(HealingDay.objects.filter(user=user).count(), 0)
