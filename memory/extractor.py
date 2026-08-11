# memory/extractor.py
"""
LLM-based memory extraction.
Analyzes conversations to extract important user facts and conversation summaries.
"""
import json
import logging
from google import genai
from google.genai import types
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction agent for a spiritual coaching AI called Soulciety.

Given a conversation between a user and the AI mentor, extract ONLY facts that the user explicitly stated about themselves. Never infer, assume, or guess.

Return valid JSON with this exact structure:
{
  "facts": [
    {
      "category": "identity|family|career|spiritual|emotional|exercises|patterns",
      "key": "descriptive_snake_case_key",
      "value": "the fact as stated by the user",
      "confidence": 0.0 to 1.0
    }
  ],
  "summary_update": "1-2 sentence summary of this conversation's key points from the user's perspective",
  "emotional_state": "primary emotional state of the user (e.g., stressed, hopeful, anxious, calm, excited)",
  "key_topics": ["topic1", "topic2"]
}

CATEGORIES AND EXPECTED KEYS:

identity: name, gender, age, age_range, location, languages, preferred_name
family: relationship_status, children, children_ages, children_names, family_dynamics, partner_details, partner_name
career: career, job_title, business, business_name, financial_situation, work_challenges, industry
spiritual: spiritual_beliefs, manifestation_goals, life_vision, goals, values, practices
emotional: recurring_struggles, belief_patterns, triggers, coping_mechanisms, mental_health_notes
exercises: practiced_exercises, exercise_feedback, daily_exercise_plan, day_count, streak
patterns: communication_style, key_breakthroughs, recurring_topics

RULES:
- Only extract facts the user DIRECTLY and EXPLICITLY stated. Do not infer hidden emotions or unstated details.
- If a fact already exists in the "existing_memories" provided, only include it if the new value is meaningfully different or updated.
- If no new facts are found, return an empty facts array.
- The summary_update should capture what the USER shared, not what the AI said.
- confidence should be 0.9+ for explicit statements, 0.7-0.9 for reasonably clear implications.
- Return ONLY valid JSON. No markdown, no explanation, no extra text."""


def extract_memories(messages, existing_memories=None):
    """
    Extract important user facts from a list of conversation messages.

    Args:
        messages: List of dicts with 'role' and 'content' keys
        existing_memories: Optional list of existing memory strings to avoid duplicates

    Returns:
        Dict with 'facts', 'summary_update', 'emotional_state', 'key_topics'
        or None if extraction fails
    """
    try:
        client = _get_client()

        # Build conversation text
        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['content']}" for msg in messages
        )

        # Build the extraction prompt
        user_prompt = f"Extract memories from this conversation:\n\n{conversation_text}"

        if existing_memories:
            existing_text = "\n".join(f"- {m}" for m in existing_memories)
            user_prompt += f"\n\nExisting memories (only extract NEW or UPDATED facts):\n{existing_text}"

        response = client.models.generate_content(
            model=settings.MEMORY_EXTRACTION_MODEL,
            config=types.GenerateContentConfig(
                system_instruction=EXTRACTION_SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            ),
            contents=[{
                "role": "user",
                "parts": [{"text": user_prompt}]
            }]
        )

        if not response or not response.text:
            logger.warning("Empty response from memory extraction model")
            return None

        # Parse JSON response
        result = json.loads(response.text.strip())

        # Validate structure
        if 'facts' not in result:
            result['facts'] = []
        if 'summary_update' not in result:
            result['summary_update'] = ''
        if 'emotional_state' not in result:
            result['emotional_state'] = ''
        if 'key_topics' not in result:
            result['key_topics'] = []

        logger.info(f"Extracted {len(result['facts'])} facts from conversation")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Memory extraction returned invalid JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Memory extraction failed: {e}")
        return None
