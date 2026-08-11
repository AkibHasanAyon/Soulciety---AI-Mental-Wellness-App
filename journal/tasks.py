# journal/tasks.py
import json
import re
import logging
from celery import shared_task
from django.utils import timezone
from .models import JournalEntry
from google import genai
from google.genai import types
from django.conf import settings
from notifications.helpers import create_notification 

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_ai_insight(self, entry_id):
    entry = None
    try:
        entry = JournalEntry.objects.get(id=entry_id)
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        mood_context = f"""The user feels {entry.mood}.""" if entry.mood else ""

        prompt = f"""
            User Content: "{entry.content}"
            {mood_context}

            Task: 
            1. Write a poetic, healing 3-sentence spiritual reflection.
            2. Create a short, soulful notification title (max 5 words) with an emoji.
            3. Create a one-sentence notification teaser.
            You must respond in valid JSON format.
                    JSON Schema:
                    {{
                        "title": "Short title with emoji",
                        "teaser": "One short notification sentence",
                        "reflection": "3-sentence poetic spiritual insight"
                    }}
            """

        response = client.models.generate_content(
            model="gemini-3.5-flash",
            config=types.GenerateContentConfig(
                temperature=0.9,
            ),
            contents=prompt
        )   

        # Check if response has content
        if not response.text:
            raise Exception("Empty response from Gemini API")

        raw_text = response.text.strip()
        
        # 2. PARSING ATTEMPT
        try:
            # Clean markdown if present (```json ... ```)
            clean_json_str = raw_text
            if clean_json_str.startswith("```"):
                clean_json_str = re.sub(r'```(?:json)?|```', '', clean_json_str).strip()

            res_data = json.loads(clean_json_str)
            insight_text = res_data.get("reflection", "")
            notif_title = res_data.get("title", "✨ A Soulful Reflection")
            notif_teaser = res_data.get("teaser", "Your insight is ready.")

            if not insight_text:
                raise ValueError("JSON valid but reflection key missing")

        except (json.JSONDecodeError, ValueError) as parse_err:
            # IF PARSING FAILS: Use the raw text but clean out JSON markers
            logger.warning(f"Parsing failed for entry {entry_id}: {parse_err}. Using cleaned raw text.")
            
            notif_title = "✨ A Moment of Light"
            notif_teaser = "Your personal reflection is ready."
            
            # Remove JSON syntax, brackets, and common labels to make it readable
            cleaned_text = re.sub(r'```(?:json)?|```', '', raw_text) # remove markdown
            cleaned_text = re.sub(r'[\{\}\[\]""]|reflection:|title:|teaser:', '', cleaned_text, flags=re.IGNORECASE)
            insight_text = cleaned_text.strip()

    except JournalEntry.DoesNotExist:
        logger.error(f"Journal entry {entry_id} not found. It may have been deleted.")
        return f"Entry {entry_id} not found"
    
    except Exception as api_err:
        # 3. GLOBAL FALLBACK (For 429 Quota or Network errors)
        logger.error(f"Gemini API Level Error for entry {entry_id}: {api_err}")
        
        # If entry doesn't exist, we can't save anything
        if entry is None:
            return f"Failed to process entry {entry_id}"
        
        notif_title = "✨ A Moment of Stillness"
        notif_teaser = "Your reflection is waiting for you."
        insight_text = (
            "Take a gentle breath. Your thoughts are valuable, and even in moments of "
            "processing, there is growth. Remember that you are exactly where you need to be. "
            "The universe is holding space for your journey."
        )
        
        # If it's a rate limit error, trigger a retry in the background
        if "429" in str(api_err):
            raise self.retry(exc=api_err, countdown=300) # Retry in 5 mins

    # 4. SAVE AND NOTIFY (only if entry exists)
    if entry:
        entry.ai_insight = insight_text
        entry.has_insight = True
        entry.insight_generated_at = timezone.now()
        entry.save(update_fields=['ai_insight', 'has_insight', 'insight_generated_at'])

        create_notification(
            user=entry.user,
            title=notif_title,
            message=notif_teaser,
            notif_type='journal_insight',
            data={"type": "journal", "entry_id": str(entry.id)}
        )

    return f"Processed entry {entry_id}"