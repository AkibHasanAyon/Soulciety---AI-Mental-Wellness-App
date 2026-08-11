# community/tasks.py
# pyrefly: ignore-errors

import logging
from celery import shared_task
from django.apps import apps
from django.conf import settings
from django.utils import timezone
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# ─── System prompt that defines the AI's voice for daily community prompts ───
PROMPT_GENERATION_SYSTEM = """You are the creative soul behind Soulciety — a spiritual growth community app.
Your job is to write ONE daily community conversation prompt that will be posted to the community feed.

THE GOAL: spark deep, authentic engagement. The user should read your prompt and immediately feel compelled to pause, reflect, and share their truth in the comments.

YOUR VOICE:
- Warm, raw, real — like a wise friend at 2 AM who asks the question nobody else dares to ask.
- Never preachy, never generic, never like a motivational poster.
- Blend spirituality with street-level realness. Think Neville Goddard meets spoken word poetry.
- Use "you" to speak directly to the reader.

PROMPT STYLE — MIX THESE FORMATS (don't always use the same one):

1. **The One-Liner Gut Punch** (1 line)
   Short, piercing, impossible to scroll past.
   Example: "What cycle are you breaking?", “What belief about yourself are you rewriting?”, “What does your highest self look like?”

2. **The Reflection Setup** (2-3 lines)
   Set a scene or context, then hit with the question.
   Example: "Most of us carry a belief about ourselves that was never ours to begin with — something someone said, a label we accepted. What belief about yourself are you finally rewriting?"

3. **The Multi-Layer Prompt** (3-4 lines)
   Build emotional momentum across lines, ending with an invitation to share.
   Example: "Close your eyes for 10 seconds. Picture the version of you who already has everything you're working toward. How do they walk? How do they speak? What does their morning look like? Now — what's one thing you can do TODAY to start being that person?"

4. **The Challenge** (2-3 lines)
   Dare the community to do something uncomfortable and share about it.
   Example: "Today's challenge: say 'no' to one thing that drains you. Just one. Then come back here and tell us how it felt."

5. **The Pattern Interrupt** (1-2 lines)
   Start with a surprising or counterintuitive statement.
   Example: "What if the thing you're most afraid of is actually the doorway? What would change if you walked through it today?"

TOPIC AREAS (rotate naturally, don't repeat the same theme on consecutive days):
- Breaking cycles and old patterns
- Rewriting self-identity and beliefs
- Envisioning your highest self
- Healing and forgiveness (self and others)
- Gratitude and recognizing growth
- Facing fears and choosing courage
- Manifesting and living in the end
- Relationships as mirrors of self-concept
- Abundance mindset and money as energy
- Finding peace in the present moment
- Community and lifting each other up

CRITICAL RULES:
- NEVER use hashtags, emojis in excessive amounts, or corporate-sounding language.
- ONE emoji maximum (use sparingly, only if it adds warmth — often none is better).
- NEVER start with "Good morning!" or "Happy [day]!" — that's basic.
- NEVER reference Neville Goddard, Joe Dispenza, Abraham Hicks, or any teacher by name.
- The prompt should feel like it came from a human, not a bot.
- Vary the length and format — don't always write the same structure.
- End in a way that makes people WANT to comment — either with a direct question, an invitation to share, or a challenge.

OUTPUT FORMAT:
Return ONLY the prompt text. No title, no label, no "Here's today's prompt:", no quotation marks wrapping the whole thing. Just the raw prompt text ready to post."""


# ─── Fallback prompts in case Gemini is unavailable ───
FALLBACK_PROMPTS = [
    "What cycle are you breaking?",
    "What belief about yourself are you rewriting?",
    "What does your highest self look like?",
    "Most of us carry a story about who we are that we didn't write. What's the story you're choosing to rewrite today?",
    "Close your eyes for 10 seconds. Picture the version of you who already has everything you're working toward. What's one thing you can do TODAY to start being that person?",
    "Today's challenge: say 'no' to one thing that drains your energy. Just one. Then come back and tell us how it felt.",
    "What would change in your life if you fully believed you deserved everything you're asking for?",
    "What are you finally ready to let go of? Say it here — sometimes typing it out is the first step.",
]

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _get_or_create_system_user():
    """Get or create the Soulciety AI system user."""
    CustomUser = apps.get_model('accounts', 'CustomUser')
    UserProfile = apps.get_model('user_profiles', 'UserProfile')

    user, created = CustomUser.objects.get_or_create(
        email='soulciety-ai@system.local',
        defaults={
            'is_active': True,
            'is_staff': False,
        }
    )

    if created:
        user.set_unusable_password()
        user.save()
        UserProfile.objects.get_or_create(
            user=user,
            defaults={'full_name': 'Soulciety AI'}
        )
        logger.info("Created Soulciety AI system user.")

    return user


def _generate_prompt_text():
    """
    Use Gemini to generate a fresh, unique daily prompt.
    Falls back to a random fallback prompt if Gemini fails.
    """
    import random

    CommunityPost = apps.get_model('community', 'CommunityPost')

    try:
        client = _get_client()

        # Gather the last 7 prompts to avoid repetition
        recent_posts = list(
            CommunityPost.objects
            .filter(user__email='soulciety-ai@system.local', is_active=True)
            .order_by('-created_at')
            .values_list('content', flat=True)[:7]
        )

        # Build the user message with recent context
        user_message = "Generate today's community conversation prompt."

        if recent_posts:
            recent_text = "\n---\n".join(recent_posts)
            user_message += (
                f"\n\nHere are the last {len(recent_posts)} prompts that were posted "
                f"(DO NOT repeat similar themes or structures):\n\n{recent_text}"
            )

        response = client.models.generate_content(
            model='gemini-3.5-flash',
            config=types.GenerateContentConfig(
                system_instruction=PROMPT_GENERATION_SYSTEM,
                temperature=1.0,  # High creativity
            ),
            contents=[{
                "role": "user",
                "parts": [{"text": user_message}]
            }]
        )

        if response and response.text:
            prompt_text = response.text.strip().strip('"\'')
            if len(prompt_text) > 10:  # Sanity check
                logger.info(f"Gemini generated prompt: {prompt_text[:60]}...")
                return prompt_text

        logger.warning("Gemini returned empty or too-short prompt, using fallback.")

    except Exception as e:
        logger.error(f"Gemini prompt generation failed: {e}")

    # Fallback: pick a random one we haven't used recently
    used_contents = set(
        CommunityPost.objects
        .filter(user__email='soulciety-ai@system.local', is_active=True)
        .order_by('-created_at')
        .values_list('content', flat=True)[:20]
    )

    available = [p for p in FALLBACK_PROMPTS if not any(p in content for content in used_contents)]
    if not available:
        available = FALLBACK_PROMPTS  # All used, reset

    fallback = random.choice(available)
    logger.info(f"Using fallback prompt: {fallback[:60]}...")
    return fallback


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def post_daily_community_prompt(self):
    """
    Daily Celery Beat task: uses Gemini AI to generate a unique community
    conversation prompt, posts it as the Soulciety AI user, and notifies everyone.
    Scheduled at 9 AM New York time.
    """
    CommunityPost = apps.get_model('community', 'CommunityPost')
    CustomUser = apps.get_model('accounts', 'CustomUser')

    try:
        # 1. Get the system user
        system_user = _get_or_create_system_user()

        # 2. Generate a fresh prompt via Gemini AI
        prompt_text = _generate_prompt_text()

        # 3. Create the community post
        post_content = f"🌟 Daily Reflection 🌟\n\n{prompt_text}"
        post = CommunityPost.objects.create(
            user=system_user,
            content=post_content,
        )

        # 4. Notify all active users
        from notifications.helpers import create_notification

        users = CustomUser.objects.filter(is_active=True).exclude(
            email='soulciety-ai@system.local'
        )
        notified = 0
        for user in users:
            try:
                create_notification(
                    user=user,
                    title="🌟 Daily Reflection",
                    message=prompt_text[:200],  # Truncate for notification
                    notif_type='daily_prompt',
                    data={"type": "community", "post_id": str(post.id)}
                )
                notified += 1
            except Exception as notify_err:
                logger.warning(f"Failed to notify user {user.id}: {notify_err}")

        logger.info(
            f"Posted AI-generated daily prompt as post {post.id}, "
            f"notified {notified} users."
        )
        return f"Posted: '{prompt_text[:60]}...' — notified {notified} users."

    except Exception as e:
        logger.error(f"Daily community prompt task error: {str(e)}", exc_info=True)
        # Retry on transient failures (DB connection, API timeout, etc.)
        raise self.retry(exc=e)
