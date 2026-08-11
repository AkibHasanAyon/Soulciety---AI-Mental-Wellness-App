from rest_framework import serializers
from .models import HealingAssessment, HealingDay, DayContent, HealingTheme, HealingStreak, HealingJourneySettings


# ──────────────────────────────────────────────
# Valid MCQ option sets (from requirements Section 2.2)
# ──────────────────────────────────────────────

Q1_CHOICES = [
    'Numb or disconnected',
    'Anxious or on edge',
    'Sad or emotionally heavy',
    'Angry or restless',
    'Lost or without direction',
    'Surprisingly okay',
]

Q3_CHOICES = [
    'Relationships & connection',
    'Self-worth & identity',
    'Career & purpose',
    'Body & physical health',
    'Family & belonging',
    'Inner peace & mental calm',
]

Q4_CHOICES = [
    'Feeling ignored, unseen, or emotionally neglected',
    'Being rejected or abandoned',
    'Being criticized, judged, or not good enough',
    'Feeling controlled, pressured, or powerless',
    "I don't fully know — just that something feels off",
]

Q5_CHOICES = [
    'Withdraw from people',
    'Overwork or stay constantly busy',
    'Distract myself (phone, content, etc.)',
    'Overeat or lose appetite',
    'Seek comfort from someone',
    'Sit with it quietly',
]

Q6_CHOICES = [
    'Being abandoned or left',
    'Being misunderstood',
    'Being controlled or losing independence',
    'Not being valued or chosen',
    'Getting too close to someone',
]

Q7_CHOICES = [
    'I am not enough',
    'No one truly stays',
    'I have to earn love',
    "The world doesn't feel safe",
    'I am broken beyond repair',
    "I don't know who I am",
]

Q8_CHOICES = [
    'Overthinking',
    'Emotional pain',
    'Loneliness',
    'Lack of direction',
    'Self-doubt',
    'Feeling stuck',
]

Q9_CHOICES = [
    "I didn't know where to start",
    'Fear of what I might uncover',
    'It felt selfish to focus on myself',
    'Lack of time or support',
    "I didn't believe I could change",
    "I tried before and it didn't work",
]


# ──────────────────────────────────────────────
# Assessment Submission Serializer
# ──────────────────────────────────────────────

class AssessmentSubmissionSerializer(serializers.Serializer):
    """
    Validates the 10-question onboarding assessment.
    Used for POST /api/healing/assessment/
    """
    q1_emotional_baseline = serializers.ChoiceField(choices=[(c, c) for c in Q1_CHOICES])
    q2_past_influence = serializers.IntegerField(min_value=1, max_value=5)
    q3_life_area_impact = serializers.ChoiceField(choices=[(c, c) for c in Q3_CHOICES])
    q4_core_pain_source = serializers.ChoiceField(choices=[(c, c) for c in Q4_CHOICES])
    q5_coping_pattern = serializers.ChoiceField(choices=[(c, c) for c in Q5_CHOICES])
    q6_relationship_fear = serializers.ChoiceField(choices=[(c, c) for c in Q6_CHOICES])
    q7_core_belief = serializers.ChoiceField(choices=[(c, c) for c in Q7_CHOICES])
    q8_desired_relief = serializers.ChoiceField(choices=[(c, c) for c in Q8_CHOICES])
    q9_healing_resistance = serializers.ChoiceField(choices=[(c, c) for c in Q9_CHOICES])
    q10_personal_desire = serializers.CharField(max_length=500, min_length=1)


# ──────────────────────────────────────────────
# Assessment Status Serializer
# ──────────────────────────────────────────────

class AssessmentStatusSerializer(serializers.ModelSerializer):
    """
    Returns polling status for plan generation.
    Used for GET /api/healing/assessment/status/
    """
    day_1_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = HealingAssessment
        fields = ['status', 'day_1_unlocked', 'journey_started_at']

    def get_day_1_unlocked(self, obj):
        return obj.status == 'ready'


# ──────────────────────────────────────────────
# Healing Profile Serializer
# ──────────────────────────────────────────────

class HealingProfileSerializer(serializers.ModelSerializer):
    """
    Returns the user's healing profile summary.
    Used for GET /api/healing/assessment/
    """
    class Meta:
        model = HealingAssessment
        fields = [
            'healing_profile',
            'status',
            'journey_started_at',
            'journey_completed_at',
        ]


# ──────────────────────────────────────────────
# Phase 4: Day Detail Serializers
# ──────────────────────────────────────────────

class BreathingExerciseSerializer(serializers.Serializer):
    """Structured breathing exercise data."""
    name = serializers.CharField()
    description = serializers.CharField()
    inhale_seconds = serializers.IntegerField()
    hold_in_seconds = serializers.IntegerField()
    exhale_seconds = serializers.IntegerField()
    hold_out_seconds = serializers.IntegerField()
    rounds = serializers.IntegerField()


class DayContentSerializer(serializers.ModelSerializer):
    """Serializes all 7 content modules for a day."""
    breathing_exercise = BreathingExerciseSerializer()

    class Meta:
        model = DayContent
        fields = [
            'guided_reflection',
            'affirmation',
            'mental_workout',
            'physical_workout',
            'breathing_exercise',
            'mini_challenge',
            'journal_prompt',
            'is_fallback',
            'generated_at',
        ]


class ThemeSerializer(serializers.ModelSerializer):
    """Serializes the day's theme data."""
    class Meta:
        model = HealingTheme
        fields = [
            'theme_title',
            'theme_intention',
            'theme_category',
            'healing_focus',
        ]


class DayDetailSerializer(serializers.ModelSerializer):
    """
    Full day response including theme, content, and state.
    Used for GET /api/healing/days/<day_number>/
    """
    theme = ThemeSerializer(read_only=True)
    content = DayContentSerializer(read_only=True)

    class Meta:
        model = HealingDay
        fields = [
            'day_number',
            'state',
            'content_status',
            'unlock_date',
            'completed_at',
            'theme',
            'content',
        ]


# ──────────────────────────────────────────────
# Phase 5: Plan Overview & Today Serializers
# ──────────────────────────────────────────────

class PlanDaySerializer(serializers.ModelSerializer):
    """
    Lightweight day serializer for the 30-day plan overview grid.
    Includes theme info + state but NOT full content.
    """
    theme_title = serializers.CharField(source='theme.theme_title', read_only=True)
    theme_intention = serializers.CharField(source='theme.theme_intention', read_only=True)
    theme_category = serializers.CharField(source='theme.theme_category', read_only=True)
    healing_focus = serializers.JSONField(source='theme.healing_focus', read_only=True)

    class Meta:
        model = HealingDay
        fields = [
            'day_number',
            'theme_title',
            'theme_intention',
            'theme_category',
            'healing_focus',
            'state',
            'unlock_date',
            'completed_at',
        ]


# ──────────────────────────────────────────────
# Phase 6: Day Completion & Progress Serializers
# ──────────────────────────────────────────────

MOOD_CHOICES = ['happy', 'fear', 'sad', 'angry', 'sick']


class DayCompleteSerializer(serializers.Serializer):
    """
    Validates input for POST /api/healing/days/<day_number>/complete/
    Both fields are optional — a day can be completed without mood or journal.
    """
    mood = serializers.ChoiceField(
        choices=[(c, c) for c in MOOD_CHOICES],
        required=False,
        allow_null=True,
    )
    journal_entry_id = serializers.IntegerField(required=False, allow_null=True)


class ProgressSerializer(serializers.ModelSerializer):
    """
    Returns streak data, milestones, and grace status.
    Used for GET /api/healing/progress/
    """
    journey_complete = serializers.SerializerMethodField()
    journey_started_at = serializers.SerializerMethodField()
    journey_completed_at = serializers.SerializerMethodField()

    class Meta:
        model = HealingStreak
        fields = [
            'total_days_completed',
            'current_streak',
            'longest_streak',
            'milestones_reached',
            'grace_period_active',
            'grace_expires_at',
            'journey_complete',
            'journey_started_at',
            'journey_completed_at',
        ]

    def _get_assessment(self, obj):
        """Fetch and cache the active assessment once per serialization."""
        if not hasattr(self, '_cached_assessment'):
            self._cached_assessment = HealingAssessment.objects.filter(
                user=obj.user, is_archived=False
            ).first()
        return self._cached_assessment

    def get_journey_complete(self, obj):
        assessment = self._get_assessment(obj)
        return assessment.journey_completed_at is not None if assessment else False

    def get_journey_started_at(self, obj):
        assessment = self._get_assessment(obj)
        return assessment.journey_started_at if assessment else None

    def get_journey_completed_at(self, obj):
        assessment = self._get_assessment(obj)
        return assessment.journey_completed_at if assessment else None


# ──────────────────────────────────────────────
# Phase 7: Settings Serializer
# ──────────────────────────────────────────────

class SettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for GET/PATCH /api/healing/settings/
    Allows updating reminder preferences and timezone.
    """
    class Meta:
        model = HealingJourneySettings
        fields = [
            'timezone',
            'morning_reminder_enabled',
            'evening_reminder_enabled',
            'morning_reminder_time',
            'evening_reminder_time',
        ]

    def validate_timezone(self, value):
        """Validate that the timezone is a valid IANA timezone."""
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, KeyError):
            raise serializers.ValidationError(f"'{value}' is not a valid timezone.")
        return value

# ──────────────────────────────────────────────
# Phase 9: Saved Affirmations & Sharing
# ──────────────────────────────────────────────

from .models import SavedAffirmation, HealingReflection

class SavedAffirmationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedAffirmation
        fields = ['id', 'text', 'day_number', 'created_at']
        read_only_fields = ['id', 'created_at']

class HealingReflectionSerializer(serializers.ModelSerializer):
    mentalreflectiontext = serializers.CharField(source='reflection_text', read_only=True)

    class Meta:
        model = HealingReflection
        fields = ['id', 'healing_day', 'mentalreflectiontext', 'created_at']
        read_only_fields = ['id', 'healing_day', 'created_at']

class ShareToCommunitySerializer(serializers.Serializer):
    TYPE_CHOICES = [
        ('affirmation', 'Affirmation'),
        ('journal', 'Journal Entry'),
    ]
    type = serializers.ChoiceField(choices=TYPE_CHOICES)
