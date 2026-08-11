# utils.py
from google import genai
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import random

# ── Gemini AI Helper ──
def get_gemini_response(user_message, conversation_history=None, user_context=""):
    """
    Generate AI response using Gemini with memory/context
    """
    genai.configure(api_key=settings.GEMINI_API_KEY)

    # Build history
    history = conversation_history or []
    if user_context:
        history.append({
            "role": "user",
            "parts": [f"Personal context about me: {user_context}"]
        })

    # Add current message
    history.append({"role": "user", "parts": [user_message]})

    model = genai.GenerativeModel(
        'gemini-3.5-flash',
        system_instruction="""
        You are Soulciety AI — a deeply compassionate, wise, and warm spiritual companion.
        You remember past conversations and speak with tenderness and spiritual depth.
        
        Respond in 2–4 short, poetic sentences only.
        Be concise, meaningful, and speak directly from the heart.
        Weave in memory naturally when relevant.
        """,
        generation_config={
            "temperature": 0.9,
            "max_output_tokens": 100,
        }
    )

    try:
        chat = model.start_chat(history=history[:-1])
        response = chat.send_message(history[-1]["parts"][0])
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return "I'm here with you, dear one. Take a gentle breath — you're held in love."

# ── Mood Helpers ──
def get_current_mood_display(user):
    """Return latest mood with emoji"""
    from app_home.models import MoodEntry
    latest = MoodEntry.objects.filter(user=user).order_by('-created_at').first()
    return latest.get_mood_display() if latest else "No mood recorded yet"

# ── Random Spiritual Quote (Fallback) ──
SPIRITUAL_QUOTES = [
    "The wound is the place where the light enters you.",
    "Be like a tree — stay grounded, keep growing, and know when to let go.",
    "You are not a drop in the ocean. You are the entire ocean in a drop.",
    "Peace begins with a smile.",
    "In the midst of movement and chaos, keep stillness inside of you.",
]

def get_fallback_quote():
    return random.choice(SPIRITUAL_QUOTES)

# ── Time Helpers ──
def is_recent(timestamp, minutes=10):
    """Check if timestamp is within last N minutes"""
    return timezone.now() - timestamp < timedelta(minutes=minutes)

# ── String Helpers ──
def truncate_text(text, max_length=100):
    return (text[:max_length] + '...') if len(text) > max_length else text