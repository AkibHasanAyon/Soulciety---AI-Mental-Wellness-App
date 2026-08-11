from django.db import models
from django.conf import settings
from django.utils import timezone


class HealingAssessment(models.Model):
    """
    Stores the user's onboarding answers (10 questions), AI-generated healing profile,
    and journey lifecycle timestamps. OneToOne with user (one active journey at a time).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healing_assessments'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Journey lifecycle timestamps
    journey_started_at = models.DateTimeField(null=True, blank=True)
    # Set when status transitions to 'ready'. Used to calculate all unlock dates.

    journey_completed_at = models.DateTimeField(null=True, blank=True)
    # Set when Day 30 is marked complete.

    # Soft-archive for journey reset flow
    is_archived = models.BooleanField(default=False)

    # ── Raw answers from the 10 assessment questions ──
    # All MCQ fields use max_length=255 to safely accommodate any future copy changes
    # on the frontend without risking DB truncation errors.

    # Q1: Emotional Baseline (single_select)
    q1_emotional_baseline = models.CharField(max_length=255)
    # Q2: Past Influence (scale 1–5)
    q2_past_influence = models.IntegerField()
    # Q3: Life Area Impact (single_select)
    q3_life_area_impact = models.CharField(max_length=255)
    # Q4: Core Pain Source (single_select)
    q4_core_pain_source = models.CharField(max_length=255)
    # Q5: Coping Pattern (single_select)
    q5_coping_pattern = models.CharField(max_length=255)
    # Q6: Relationship Fear (single_select)
    q6_relationship_fear = models.CharField(max_length=255)
    # Q7: Core Belief (single_select)
    q7_core_belief = models.CharField(max_length=255)
    # Q8: Desired Relief (single_select)
    q8_desired_relief = models.CharField(max_length=255)
    # Q9: Healing Resistance (single_select)
    q9_healing_resistance = models.CharField(max_length=255)
    # Q10: Personal Desire (free-form text, max 500 chars)
    q10_personal_desire = models.TextField(max_length=500)

    # AI-generated healing profile (JSON — see requirements Section 3.2)
    healing_profile = models.JSONField(null=True, blank=True)

    # Plan generation status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    generation_error = models.TextField(blank=True)

    @property
    def journey_start_date(self):
        """Returns the DATE portion of journey_started_at in UTC. Used for unlock date math."""
        if self.journey_started_at:
            return self.journey_started_at.date()
        return None

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(is_archived=False),
                name='unique_active_assessment'
            )
        ]

    def __str__(self):
        status_label = "ARCHIVED" if self.is_archived else self.status
        return f"HealingAssessment for {self.user} ({status_label})"


class HealingJourneySettings(models.Model):
    """
    Stores per-user journey preferences and timezone.
    Created atomically with HealingStreak inside generate_healing_plan.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healing_settings'
    )

    # Timezone (IANA string, e.g. "America/New_York")
    # Populated from the mobile client's reported timezone at assessment submission.
    # Falls back to "UTC" if not provided.
    timezone = models.CharField(max_length=64, default='UTC')

    # Reminder preferences
    morning_reminder_enabled = models.BooleanField(default=True)
    evening_reminder_enabled = models.BooleanField(default=True)
    morning_reminder_time = models.TimeField(default='07:00')   # In user's local time
    evening_reminder_time = models.TimeField(default='20:00')   # In user's local time

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"HealingSettings for {self.user} (tz={self.timezone})"


class HealingTheme(models.Model):
    """
    Stores the 30 AI-generated themes for a user's journey.
    Each theme represents one day's overarching topic in the healing arc.
    """
    CATEGORY_CHOICES = [
        ('Foundation', 'Foundation'),       # Days 1–5
        ('Awareness', 'Awareness'),         # Days 6–10
        ('Release', 'Release'),             # Days 11–15
        ('Rewiring', 'Rewiring'),           # Days 16–20
        ('Embodiment', 'Embodiment'),       # Days 21–25
        ('Integration', 'Integration'),     # Days 26–30
    ]

    assessment = models.ForeignKey(
        HealingAssessment,
        on_delete=models.CASCADE,
        related_name='themes'
    )
    day_number = models.IntegerField()                                          # 1–30
    theme_title = models.CharField(max_length=200)
    theme_intention = models.CharField(max_length=300)
    theme_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    healing_focus = models.JSONField(default=list)                              # e.g. ["self-compassion", "grounding"]

    class Meta:
        unique_together = ('assessment', 'day_number')
        ordering = ['day_number']

    def __str__(self):
        return f"Day {self.day_number}: {self.theme_title}"


class HealingDay(models.Model):
    """
    Tracks each day's lifecycle: unlock date, state, completion,
    and links to mood/journal entries.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healing_days'
    )
    theme = models.ForeignKey(
        HealingTheme,
        on_delete=models.CASCADE,
        related_name='days'
    )
    day_number = models.IntegerField()
    unlock_date = models.DateField()
    # Pre-calculated at plan generation: journey_start_date + (day_number - 1) days

    completed_at = models.DateTimeField(null=True, blank=True)

    mood_entry = models.ForeignKey(
        'app_home.MoodEntry',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    journal_entry = models.ForeignKey(
        'journal.JournalEntry',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # Content generation status
    CONTENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('generating', 'Generating'),
        ('ready', 'Ready'),
        ('failed', 'Failed'),       # After 3 retries; fallback content served
    ]
    content_status = models.CharField(max_length=20, choices=CONTENT_STATUS_CHOICES, default='pending')

    # Day state machine
    STATE_CHOICES = [
        ('locked', 'Locked'),
        ('available', 'Available'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    ]
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='locked')

    class Meta:
        ordering = ['day_number']

    def __str__(self):
        return f"{self.user} — Day {self.day_number} ({self.state})"


class DayContent(models.Model):
    """
    Stores all AI-generated content for a single day's session (7 modules).
    One-to-one with HealingDay.
    """
    healing_day = models.OneToOneField(
        HealingDay,
        on_delete=models.CASCADE,
        related_name='content'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    is_fallback = models.BooleanField(default=False)
    # True if this content was served from the hardcoded fallback bank (AI unavailable)

    # Module 1: Guided Reflection (200–350 words, poetic, warm)
    guided_reflection = models.TextField()

    # Module 2: Daily Affirmation (1–3 sentences, "I AM" language)
    affirmation = models.TextField()

    # Module 3: Mental Workout (100–200 words, active cognitive exercise)
    mental_workout = models.TextField()

    # Module 4: Physical Workout (JSON object with title, instructions, duration_seconds)
    physical_workout = models.JSONField()

    # Module 5: Breathing Exercise (structured JSON — see requirements Section 5.5)
    # JSON format: {name, description, inhale_seconds, hold_in_seconds,
    #               exhale_seconds, hold_out_seconds, rounds}
    breathing_exercise = models.JSONField()

    # Module 6: Mini Challenge (1–2 sentences, real-world behavior)
    mini_challenge = models.TextField()

    # Module 7: Journal Prompt (one open-ended question)
    journal_prompt = models.TextField()

    def __str__(self):
        src = "fallback" if self.is_fallback else "AI"
        return f"Content for Day {self.healing_day.day_number} ({src})"


class HealingStreak(models.Model):
    """
    Tracks streak state per user. Created atomically with HealingJourneySettings
    inside generate_healing_plan. One per user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healing_streak'
    )
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_completed_date = models.DateField(null=True, blank=True)
    total_days_completed = models.IntegerField(default=0)
    milestones_reached = models.JSONField(default=list)     # e.g. [3, 7, 14]

    # Grace period fields
    grace_period_active = models.BooleanField(default=False)
    grace_expires_at = models.DateTimeField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Streak for {self.user} (current={self.current_streak})"


class SavedAffirmation(models.Model):
    """
    Stores daily affirmations that the user has explicitly saved/favorited.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_affirmations'
    )
    text = models.TextField()
    day_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'text')

    def __str__(self):
        return f"Affirmation for {self.user}: {self.text[:50]}..."

class HealingReflection(models.Model):
    """
    Stores user reflections/notes from specific exercises (e.g., Mental Workout)
    during a Healing Day.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='healing_reflections'
    )
    healing_day = models.ForeignKey(
        HealingDay,
        on_delete=models.CASCADE,
        related_name='reflections'
    )
    reflection_text = models.TextField(help_text="The user's written reflection from the exercise.")
    created_at = models.DateTimeField(auto_now_add=True)
    extracted_to_memory = models.BooleanField(
        default=False,
        help_text="Whether this reflection has been processed by the memory extractor."
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Reflection for Day {self.healing_day.day_number} ({self.user})"
