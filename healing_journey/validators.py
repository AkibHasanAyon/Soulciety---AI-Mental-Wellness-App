# healing_journey/validators.py
"""
JSON validation helpers for Gemini AI responses.
Used to validate plan generation output and daily content output before saving to DB.
"""
import logging

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Required keys for healing profile
# ──────────────────────────────────────────────

HEALING_PROFILE_REQUIRED_KEYS = [
    'emotional_state',
    'trauma_type',
    'core_wound',
    'life_domain',
    'coping_style',
    'attachment_pattern',
    'primary_healing_goal',
    'healing_blockers',
    'personal_desire',
    'healing_arc_summary',
]

# Valid theme categories matching the 6-phase arc
VALID_THEME_CATEGORIES = [
    'Foundation',
    'Awareness',
    'Release',
    'Rewiring',
    'Embodiment',
    'Integration',
]


class PlanValidationError(Exception):
    """Raised when AI-generated plan data fails validation."""
    pass


class ContentValidationError(Exception):
    """Raised when AI-generated daily content fails validation."""
    pass


# ──────────────────────────────────────────────
# Plan Generation Validators
# ──────────────────────────────────────────────

def validate_healing_profile(data):
    """
    Validate the AI-generated healing profile JSON.

    Args:
        data: dict — the healing_profile object from the AI response

    Raises:
        PlanValidationError: if validation fails

    Returns:
        dict — the validated profile data
    """
    if not isinstance(data, dict):
        raise PlanValidationError(f"healing_profile must be a dict, got {type(data).__name__}")

    missing_keys = [k for k in HEALING_PROFILE_REQUIRED_KEYS if k not in data]
    if missing_keys:
        raise PlanValidationError(f"healing_profile missing keys: {missing_keys}")

    empty_keys = [k for k in HEALING_PROFILE_REQUIRED_KEYS if not data.get(k)]
    if empty_keys:
        raise PlanValidationError(f"healing_profile has empty values for keys: {empty_keys}")

    return data


def validate_themes(themes):
    """
    Validate the AI-generated themes array (30 themes).

    Args:
        themes: list — array of 30 theme objects

    Raises:
        PlanValidationError: if validation fails

    Returns:
        list — the validated themes list
    """
    if not isinstance(themes, list):
        raise PlanValidationError(f"themes must be a list, got {type(themes).__name__}")

    if len(themes) != 30:
        raise PlanValidationError(f"Expected exactly 30 themes, got {len(themes)}")

    seen_day_numbers = set()
    for i, theme in enumerate(themes):
        if not isinstance(theme, dict):
            raise PlanValidationError(f"Theme at index {i} must be a dict, got {type(theme).__name__}")

        # Check required keys
        required_keys = ['day_number', 'theme_title', 'theme_intention', 'theme_category', 'healing_focus']
        missing = [k for k in required_keys if k not in theme]
        if missing:
            raise PlanValidationError(f"Theme at index {i} missing keys: {missing}")

        # Validate day_number
        day_num = theme['day_number']
        if not isinstance(day_num, int) or day_num < 1 or day_num > 30:
            raise PlanValidationError(f"Theme at index {i} has invalid day_number: {day_num}")

        if day_num in seen_day_numbers:
            raise PlanValidationError(f"Duplicate day_number: {day_num}")
        seen_day_numbers.add(day_num)

        # Validate theme_category
        if theme['theme_category'] not in VALID_THEME_CATEGORIES:
            raise PlanValidationError(
                f"Theme at day {day_num} has invalid category: '{theme['theme_category']}'. "
                f"Must be one of: {VALID_THEME_CATEGORIES}"
            )

        # Validate non-empty strings
        if not theme.get('theme_title'):
            raise PlanValidationError(f"Theme at day {day_num} has empty theme_title")
        if not theme.get('theme_intention'):
            raise PlanValidationError(f"Theme at day {day_num} has empty theme_intention")

        # Validate healing_focus is a non-empty list
        focus = theme.get('healing_focus')
        if not isinstance(focus, list) or len(focus) == 0:
            raise PlanValidationError(f"Theme at day {day_num} has invalid healing_focus: must be a non-empty list")

    # Verify we have all 30 sequential day numbers
    if seen_day_numbers != set(range(1, 31)):
        missing_days = set(range(1, 31)) - seen_day_numbers
        raise PlanValidationError(f"Missing day_numbers: {sorted(missing_days)}")

    return themes


def validate_plan_response(data):
    """
    Validate the full AI response for plan generation.

    Args:
        data: dict — the full parsed JSON response

    Raises:
        PlanValidationError: if validation fails

    Returns:
        tuple — (healing_profile, themes) both validated
    """
    if not isinstance(data, dict):
        raise PlanValidationError(f"Response must be a dict, got {type(data).__name__}")

    if 'healing_profile' not in data:
        raise PlanValidationError("Response missing 'healing_profile' key")
    if 'themes' not in data:
        raise PlanValidationError("Response missing 'themes' key")

    healing_profile = validate_healing_profile(data['healing_profile'])
    themes = validate_themes(data['themes'])

    return healing_profile, themes


# ──────────────────────────────────────────────
# Daily Content Validators (Phase 4 — placeholders active)
# ──────────────────────────────────────────────

CONTENT_REQUIRED_KEYS = [
    'guided_reflection',
    'affirmation',
    'mental_workout',
    'physical_workout',
    'breathing_exercise',
    'mini_challenge',
    'journal_prompt',
]

BREATHING_EXERCISE_REQUIRED_KEYS = [
    'name',
    'description',
    'inhale_seconds',
    'hold_in_seconds',
    'exhale_seconds',
    'hold_out_seconds',
    'rounds',
]


def validate_breathing_exercise(data):
    """
    Validate the breathing exercise structured JSON.

    Args:
        data: dict — the breathing_exercise object

    Raises:
        ContentValidationError: if validation fails

    Returns:
        dict — validated breathing data
    """
    if not isinstance(data, dict):
        raise ContentValidationError(f"breathing_exercise must be a dict, got {type(data).__name__}")

    missing = [k for k in BREATHING_EXERCISE_REQUIRED_KEYS if k not in data]
    if missing:
        raise ContentValidationError(f"breathing_exercise missing keys: {missing}")

    # Range validations
    checks = {
        'inhale_seconds': (3, 6),
        'hold_in_seconds': (0, 8),
        'exhale_seconds': (4, 10),
        'hold_out_seconds': (0, 4),
        'rounds': (3, 8),
    }
    for key, (min_val, max_val) in checks.items():
        val = data[key]
        if not isinstance(val, int):
            raise ContentValidationError(f"breathing_exercise.{key} must be int, got {type(val).__name__}")
        if val < min_val or val > max_val:
            raise ContentValidationError(
                f"breathing_exercise.{key} = {val} is out of range [{min_val}, {max_val}]"
            )

    return data


def validate_physical_workout(data):
    """
    Validate the physical workout structured JSON.

    Args:
        data: dict — the physical_workout object

    Raises:
        ContentValidationError: if validation fails

    Returns:
        dict — validated physical workout data
    """
    if not isinstance(data, dict):
        raise ContentValidationError(f"physical_workout must be a dict, got {type(data).__name__}")

    required_keys = ['title', 'instructions', 'duration_seconds']
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ContentValidationError(f"physical_workout missing keys: {missing}")

    if not isinstance(data['title'], str) or not data['title'].strip():
        raise ContentValidationError("physical_workout.title must be a non-empty string")
    
    if not isinstance(data['instructions'], str) or not data['instructions'].strip():
        raise ContentValidationError("physical_workout.instructions must be a non-empty string")
        
    if not isinstance(data['duration_seconds'], int):
        raise ContentValidationError(f"physical_workout.duration_seconds must be an int, got {type(data['duration_seconds']).__name__}")

    return data


def validate_day_content(data):
    """
    Validate the AI-generated daily content (7 modules).

    Args:
        data: dict — the full content response

    Raises:
        ContentValidationError: if validation fails

    Returns:
        dict — validated content data
    """
    if not isinstance(data, dict):
        raise ContentValidationError(f"Content must be a dict, got {type(data).__name__}")

    missing = [k for k in CONTENT_REQUIRED_KEYS if k not in data]
    if missing:
        raise ContentValidationError(f"Content missing keys: {missing}")

    text_fields = [
        'guided_reflection', 'affirmation', 'mental_workout',
        'mini_challenge', 'journal_prompt',
    ]
    for field in text_fields:
        if not data.get(field) or not isinstance(data[field], str) or not data[field].strip():
            raise ContentValidationError(f"Content field '{field}' is empty or not a string")

    # Validate structured modules
    validate_physical_workout(data['physical_workout'])
    validate_breathing_exercise(data['breathing_exercise'])

    return data
