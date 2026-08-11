# healing_journey/fallbacks.py
"""
Hardcoded fallback content bank — one complete 7-module set per healing phase.
Used as a safety net when Gemini AI is unavailable after 3 retries.
Users never see an empty/broken screen.

Content was written to match the Soulciety voice: warm, supportive, uplifting,
higher-consciousness focused. Never religious. No toxic positivity.
"""


FALLBACK_CONTENT_BANK = {

    # ─── Phase 1: Foundation (Days 1–5) ───
    'Foundation': {
        'guided_reflection': (
            "Welcome, beautiful soul. Today you begin something quiet but "
            "revolutionary — you begin choosing yourself. Not the polished version "
            "the world asks for, but the real you. The one who carries invisible "
            "weight and still keeps going.\n\n"
            "This journey is not about fixing what's broken. Nothing in you is broken. "
            "It's about coming home to the parts of yourself you've been too afraid to "
            "visit. The parts that ache. The parts that remember.\n\n"
            "Right now, you don't need to do anything grand. Just breathe. Just be here. "
            "This is your sacred ground — a place where your pain is not a problem to "
            "solve but a story worth hearing. You are safe here. You are seen here.\n\n"
            "Today, we lay the foundation. Not with force — with gentleness. The kind "
            "of gentleness you've been waiting for someone else to offer you. But it "
            "starts here, with you, offering it to yourself."
        ),
        'affirmation': (
            "I am allowed to take up space. I am allowed to feel what I feel. "
            "My healing has already begun, simply by showing up."
        ),
        'mental_workout': (
            "Close your eyes for a moment. Think of one belief you carry about yourself — "
            "something heavy, something old. Write it down. Now ask yourself: "
            "\"Who first told me this? Was it my voice, or someone else's?\" "
            "If it wasn't originally yours, you have permission to question it. "
            "Write one sentence that begins with: \"What if instead, I...\" "
            "You don't have to believe the new sentence yet. Just let it exist."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Stand up gently. Place both feet flat on the ground. Feel the floor beneath you — "
            "solid, steady, holding you. Take three slow breaths.\n\n"
            "Now, starting from your toes, slowly tense each muscle group for 5 seconds "
            "and release: feet, calves, thighs, belly, chest, shoulders, fists, jaw. "
            "With each release, imagine that tension leaving your body like steam. "
            "Finish by shaking your hands gently for 10 seconds. You've just told your "
            "nervous system: you are safe."),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': 'Grounding Breath',
            'description': 'A simple breathing pattern to activate your parasympathetic nervous system and bring you into the present moment.',
            'inhale_seconds': 4,
            'hold_in_seconds': 4,
            'exhale_seconds': 6,
            'hold_out_seconds': 2,
            'rounds': 5,
        },
        'mini_challenge': (
            "Before bed tonight, place your hand on your chest and say out loud: "
            "\"I am here. I am safe. I am beginning.\""
        ),
        'journal_prompt': (
            "What is one thing you've been carrying that no longer belongs to you — "
            "and what would it feel like to set it down?"
        ),
    },

    # ─── Phase 2: Awareness (Days 6–10) ───
    'Awareness': {
        'guided_reflection': (
            "Now that you've built a little ground beneath your feet, it's time to "
            "look — really look — at the patterns you've been living inside. Not to "
            "judge them. Not to be ashamed. But to see them clearly, maybe for the "
            "first time.\n\n"
            "We all carry patterns. Ways we learned to survive. Ways we protected "
            "ourselves when we didn't have the tools to do it differently. Those "
            "patterns were intelligent once — they kept you alive. But some of them "
            "are running on autopilot now, long after the danger has passed.\n\n"
            "Today, your only job is to observe. To notice without reacting. When "
            "you feel a familiar pull — the urge to withdraw, to people-please, to "
            "numb, to control — just whisper to yourself: \"I see you. I understand "
            "why you're here.\"\n\n"
            "Awareness is not a weapon. It's a lantern. And you're learning to carry it."
        ),
        'affirmation': (
            "I am becoming aware of my patterns, and that awareness is my power. "
            "I do not need to be ashamed of how I survived."
        ),
        'mental_workout': (
            "Think about a recent situation that triggered a strong emotional reaction — "
            "anxiety, anger, withdrawal, or people-pleasing. Replay it like a movie in "
            "your mind, but this time you're the director, not the actor.\n\n"
            "Ask yourself these three questions:\n"
            "1. What feeling came first — before the reaction?\n"
            "2. Does this feeling remind me of something older?\n"
            "3. What was I actually trying to protect?\n\n"
            "Write your answers down. No judgment — just data about your inner world."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Find a quiet spot. Stand or sit comfortably. Begin gently rotating your "
            "neck in slow circles — 5 times clockwise, 5 times counter-clockwise. "
            "Then roll your shoulders forward 5 times, backward 5 times.\n\n"
            "Now place both hands on your belly. Breathe deeply — feel your belly "
            "expand, then contract. Do this for one full minute. This is called "
            "belly breathing, and it tells your vagus nerve that you are safe. "
            "Finish by gently pressing your feet into the ground and wiggling your toes."),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': '4-7-8 Calming Breath',
            'description': 'This pattern extends the exhale to activate the relaxation response, perfect for moments of heightened awareness.',
            'inhale_seconds': 4,
            'hold_in_seconds': 7,
            'exhale_seconds': 8,
            'hold_out_seconds': 0,
            'rounds': 4,
        },
        'mini_challenge': (
            "The next time you feel a familiar emotional pattern activate today — "
            "pause for three seconds before responding. Just three seconds. "
            "Notice what happens in that gap."
        ),
        'journal_prompt': (
            "What emotional pattern keeps showing up in your life — and when did you "
            "first learn it was the way to stay safe?"
        ),
    },

    # ─── Phase 3: Release (Days 11–15) ───
    'Release': {
        'guided_reflection': (
            "There comes a point in every healing journey where the work shifts. "
            "You've seen the patterns. You've felt the weight. And now — gently, "
            "bravely — you begin to let go.\n\n"
            "Letting go is not forgetting. It's not pretending it didn't happen. "
            "It's not swallowing your pain and calling it peace. Letting go is "
            "choosing to stop carrying what was never yours to hold.\n\n"
            "Maybe it's a grudge. Maybe it's a version of yourself you outgrew. "
            "Maybe it's a grief you never let yourself fully feel. Whatever it is, "
            "it has been asking for your attention — not so you can fix it, but so "
            "you can finally set it free.\n\n"
            "You do not need to release everything today. Just one thing. One small "
            "stone from the weight on your chest. That's enough. That's everything."
        ),
        'affirmation': (
            "I release what no longer serves me. I am not betraying my past by "
            "choosing my peace. I deserve to feel light."
        ),
        'mental_workout': (
            "Write a letter you'll never send. Address it to someone who hurt you, "
            "to a version of yourself you've outgrown, or to a situation you wish "
            "had gone differently.\n\n"
            "Don't filter it. Don't make it kind. Let the raw truth pour out — "
            "the anger, the grief, the confusion. When you're done, read it once. "
            "Then close it. You've given voice to something that has been silent "
            "for too long."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Stand up. Shake your entire body for two full minutes. Start with your "
            "hands — shake them fast and loose. Then your arms. Then shimmy your "
            "shoulders. Let it move through your torso, your hips, your legs.\n\n"
            "This isn't exercise — this is somatic release. Animals in the wild do "
            "this after a threat passes: they literally shake the stress out of "
            "their bodies. You are doing the same. Shake it out. Let it go."),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': 'Releasing Sigh Breath',
            'description': 'An extended exhale with an audible sigh helps discharge stored emotional tension from your body.',
            'inhale_seconds': 4,
            'hold_in_seconds': 2,
            'exhale_seconds': 8,
            'hold_out_seconds': 2,
            'rounds': 6,
        },
        'mini_challenge': (
            "Identify one thing you've been holding onto that you're ready to release. "
            "Write it on a piece of paper. Then tear the paper up. Let it go physically."
        ),
        'journal_prompt': (
            "What are you holding onto that you know — deep down — is no longer "
            "yours to carry?"
        ),
    },

    # ─── Phase 4: Rewiring (Days 16–20) ───
    'Rewiring': {
        'guided_reflection': (
            "You've done something remarkable. You've looked at your wounds. You've "
            "started to release. And now comes the most powerful phase — the one where "
            "you begin to build something new in the space that opened up.\n\n"
            "This is rewiring. Not just thinking positive thoughts — that's surface "
            "level. This is about going into the operating system of your identity and "
            "rewriting the code. The code that says you're not enough. The code that "
            "says love must be earned. The code that says the world isn't safe.\n\n"
            "Those programs ran for years. They won't change overnight. But they do "
            "change — one deliberate thought at a time. One new belief chosen with "
            "intention and repeated until it becomes your truth.\n\n"
            "Today, you start writing a new story. Not the one that was written for "
            "you — the one you choose."
        ),
        'affirmation': (
            "I am rewriting my story. The old beliefs had their purpose — and now I "
            "choose new ones. I am becoming who I was always meant to be."
        ),
        'mental_workout': (
            "Identify your most persistent negative self-talk pattern — the thought "
            "that plays on repeat when you're stressed or alone.\n\n"
            "Write it down word for word. Now directly beneath it, write a counter-"
            "statement. Not a denial — a redirect. For example:\n"
            "Old: \"I always mess things up.\"\n"
            "New: \"I am learning, and learning is not failing.\"\n\n"
            "Read the new statement out loud three times. Let it feel strange. "
            "That strangeness means it's new — and new is exactly what you need."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Find a mirror. Stand in front of it. This might feel awkward — that's "
            "normal. Look at yourself. Not at your appearance — at your eyes.\n\n"
            "Place one hand on your heart. Say out loud: \"I am safe. I am worthy. "
            "I am learning to be good to myself.\" Hold eye contact with yourself "
            "for 30 seconds. Then take three deep breaths. This is called mirror work, "
            "and it is one of the most powerful rewiring tools that exists."),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': 'Energizing Breath',
            'description': 'Equal inhale and exhale with a brief hold creates balance and activates your sympathetic and parasympathetic systems equally.',
            'inhale_seconds': 5,
            'hold_in_seconds': 3,
            'exhale_seconds': 5,
            'hold_out_seconds': 0,
            'rounds': 6,
        },
        'mini_challenge': (
            "Catch yourself in one moment of negative self-talk today. Pause. "
            "Replace it with: \"That's the old story. Here's the new one:\" "
            "and finish the sentence."
        ),
        'journal_prompt': (
            "If you could install one new belief about yourself — something you'd "
            "wake up truly believing tomorrow — what would it be, and how would "
            "your life look different?"
        ),
    },

    # ─── Phase 5: Embodiment (Days 21–25) ───
    'Embodiment': {
        'guided_reflection': (
            "Something has shifted, and you can feel it. Maybe it's subtle — a "
            "gentler voice in your head, a moment of calm where chaos used to live, "
            "a choice you made that past-you wouldn't have.\n\n"
            "This is embodiment. It's when healing stops being a concept and starts "
            "becoming how you live. Not perfectly — never perfectly — but intentionally.\n\n"
            "Embodiment is choosing the new you in the small moments: how you speak "
            "to yourself in the morning, how you respond when triggered, how you "
            "hold boundaries without guilt, how you receive love without suspicion.\n\n"
            "You are no longer just knowing the truth. You are living it. One small, "
            "imperfect, courageous choice at a time. And that — more than any "
            "affirmation — is what changes a life."
        ),
        'affirmation': (
            "I am not just healing — I am becoming. I embody my new truth in every "
            "choice I make. I am the living proof of my own transformation."
        ),
        'mental_workout': (
            "Think about the version of you who has fully healed — the person you're "
            "becoming. Answer these questions as that person:\n\n"
            "1. How do I start my mornings?\n"
            "2. How do I respond when someone criticizes me?\n"
            "3. What do I say when I look in the mirror?\n"
            "4. How do I show up in my closest relationship?\n\n"
            "Now choose ONE of those answers and practice it today — literally. "
            "Act as if you already are that person. Because you're closer than you think."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Take a five-minute mindful walk. It can be anywhere — around your room, "
            "your block, your office. The only rule: no phone, no music.\n\n"
            "With each step, feel your foot press into the ground. Notice the air "
            "on your skin. Listen to the sounds around you without labeling them. "
            "If your mind wanders — and it will — gently bring it back to your feet.\n\n"
            "This is embodied presence. You're teaching your nervous system that "
            "right now, in this moment, you are safe and whole."),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': 'Heart-Centered Breath',
            'description': 'Breathing with awareness focused on the heart space cultivates emotional coherence and self-connection.',
            'inhale_seconds': 5,
            'hold_in_seconds': 5,
            'exhale_seconds': 5,
            'hold_out_seconds': 0,
            'rounds': 5,
        },
        'mini_challenge': (
            "Choose one interaction today — with a friend, a coworker, a stranger — "
            "and show up as your healed self. Speak with intention. "
            "Listen without planning your response."
        ),
        'journal_prompt': (
            "In what moment this week did you surprise yourself by responding "
            "differently than you would have before — and how did it feel?"
        ),
    },

    # ─── Phase 6: Integration (Days 26–30) ───
    'Integration': {
        'guided_reflection': (
            "You've walked 30 days into yourself. Not around yourself — into. "
            "Into the pain. Into the patterns. Through the release. Through the "
            "rewiring. And now you stand here — not at an ending, but at a beginning "
            "with depth.\n\n"
            "Integration is the most underrated phase of healing. It's where you "
            "stop doing the healing work as a project and start letting it be your "
            "life. Where the boundaries, the beliefs, the breath, the compassion — "
            "they become second nature.\n\n"
            "You are not the person who started this journey. And that's not loss — "
            "it's graduation. You didn't abandon your old self. You held them, "
            "honored them, and gently guided them into a wider way of being.\n\n"
            "This is who you are now. Not someone who healed once — someone who knows "
            "how to heal again, whenever life asks you to."
        ),
        'affirmation': (
            "I am whole. Not because I'm perfect — but because I've learned to hold "
            "all of who I am with compassion. My healing is a lifelong practice, "
            "and I trust myself to keep walking."
        ),
        'mental_workout': (
            "It's time for a full-circle reflection. Write down three things:\n\n"
            "1. The belief I held about myself when I started this journey.\n"
            "2. The moment during these 30 days that shifted something.\n"
            "3. The truth I know about myself now that I didn't know before.\n\n"
            "Read all three aloud. Notice the distance between #1 and #3. "
            "That distance? You walked it. One day at a time."
        ),
        'physical_workout': {
            'title': 'Body Release Practice',
            'instructions': ("Sit comfortably with your eyes closed. Place one hand on your heart "
            "and one on your belly. Breathe deeply for one minute.\n\n"
            "Now, starting from the top of your head, slowly scan down through your "
            "body. Don't change anything — just notice. What feels tight? What feels "
            "open? Where is there warmth? Where is there numbness?\n\n"
            "When you reach your feet, take three deep breaths and whisper: "
            "\"Thank you, body, for carrying me through all of this.\""),
            'duration_seconds': 120,
        },
        'breathing_exercise': {
            'name': 'Wholeness Breath',
            'description': 'A balanced, rhythmic breath that symbolizes integration — equal parts receiving and releasing, just like life.',
            'inhale_seconds': 5,
            'hold_in_seconds': 5,
            'exhale_seconds': 5,
            'hold_out_seconds': 3,
            'rounds': 5,
        },
        'mini_challenge': (
            "Write a short letter to yourself — from your healed self to the "
            "person who started this journey. Tell them what you wish they knew. "
            "Keep it somewhere you'll find it again."
        ),
        'journal_prompt': (
            "If you could go back to Day 1 and tell that version of yourself one "
            "thing — what would it be?"
        ),
    },
}


def get_fallback_content(theme_category):
    """
    Retrieve fallback content for a given healing phase.

    Args:
        theme_category: str — one of Foundation, Awareness, Release, Rewiring, Embodiment, Integration

    Returns:
        dict — a complete 7-module content set

    Raises:
        KeyError: if the theme_category is not found
    """
    if theme_category not in FALLBACK_CONTENT_BANK:
        raise KeyError(
            f"No fallback content for theme_category '{theme_category}'. "
            f"Valid categories: {list(FALLBACK_CONTENT_BANK.keys())}"
        )
    return FALLBACK_CONTENT_BANK[theme_category].copy()


FALLBACK_HEALING_PROFILE = {'emotional_state': 'in need of gentle recalibration and nervous system regulation', 'trauma_type': 'accumulated life stressors and emotional disconnection', 'core_wound': 'disconnection from true self and innate worthiness', 'life_domain': 'inner peace, self-worth, and authentic relationships', 'coping_style': 'withdrawing, over-functioning, or seeking external validation', 'attachment_pattern': 'seeking external safety rather than internal grounding', 'primary_healing_goal': 'reconnecting with inner stillness, rebuilding self-trust, and feeling safe', 'healing_blockers': 'fear of feeling deeply, rushing the process, self-judgment', 'personal_desire': 'to feel whole, grounded, and at home in my own body again', 'healing_arc_summary': 'Over the next 30 days, you will journey through safety, awareness, and release. You will gently rewire old patterns and step into a more embodied, integrated version of yourself.'}

FALLBACK_THEMES = [{'day_number': 1, 'theme_category': 'Foundation', 'theme_title': 'The First Step', 'theme_intention': 'Today I give myself permission to begin.', 'healing_focus': ['safety', 'grounding']}, {'day_number': 2, 'theme_category': 'Foundation', 'theme_title': 'Coming Back to the Body', 'theme_intention': 'I am learning to be present with my physical self.', 'healing_focus': ['somatic connection', 'presence']}, {'day_number': 3, 'theme_category': 'Foundation', 'theme_title': 'Creating Inner Safety', 'theme_intention': 'I am building a safe space within myself.', 'healing_focus': ['inner sanctuary', 'calm']}, {'day_number': 4, 'theme_category': 'Foundation', 'theme_title': 'The Weight I Carry', 'theme_intention': 'I acknowledge my burdens without shame.', 'healing_focus': ['acknowledgment', 'self-compassion']}, {'day_number': 5, 'theme_category': 'Foundation', 'theme_title': 'Gentle Acceptance', 'theme_intention': 'I accept exactly where I am today.', 'healing_focus': ['acceptance', 'non-judgment']}, {'day_number': 6, 'theme_category': 'Awareness', 'theme_title': 'Noticing the Noise', 'theme_intention': 'I am observing my thoughts without attachment.', 'healing_focus': ['mindfulness', 'observation']}, {'day_number': 7, 'theme_category': 'Awareness', 'theme_title': 'The Stories I Tell', 'theme_intention': 'I am aware of the narratives I repeat.', 'healing_focus': ['narrative shift', 'truth']}, {'day_number': 8, 'theme_category': 'Awareness', 'theme_title': 'Identifying Triggers', 'theme_intention': 'I am learning the language of my reactions.', 'healing_focus': ['emotional triggers', 'curiosity']}, {'day_number': 9, 'theme_category': 'Awareness', 'theme_title': 'The Echoes of the Past', 'theme_intention': 'I see how the past influences my present.', 'healing_focus': ['past wounds', 'clarity']}, {'day_number': 10, 'theme_category': 'Awareness', 'theme_title': 'Meeting My Inner Child', 'theme_intention': 'I offer compassion to the younger version of me.', 'healing_focus': ['inner child', 'warmth']}, {'day_number': 11, 'theme_category': 'Release', 'theme_title': 'Exhaling the Old', 'theme_intention': 'I release what is no longer mine to carry.', 'healing_focus': ['letting go', 'exhale']}, {'day_number': 12, 'theme_category': 'Release', 'theme_title': 'Unclenching the Grip', 'theme_intention': 'I surrender the need for absolute control.', 'healing_focus': ['surrender', 'trust']}, {'day_number': 13, 'theme_category': 'Release', 'theme_title': 'Grieving What Was', 'theme_intention': 'I honor my losses to make space for peace.', 'healing_focus': ['grief', 'honoring']}, {'day_number': 14, 'theme_category': 'Release', 'theme_title': 'Forgiving the Moment', 'theme_intention': 'I offer grace to myself and my journey.', 'healing_focus': ['forgiveness', 'grace']}, {'day_number': 15, 'theme_category': 'Release', 'theme_title': 'Emptying the Cup', 'theme_intention': 'I create space for new beginnings.', 'healing_focus': ['space-making', 'clearing']}, {'day_number': 16, 'theme_category': 'Rewiring', 'theme_title': 'A New Narrative', 'theme_intention': 'I am writing a story of empowerment.', 'healing_focus': ['empowerment', 'new beliefs']}, {'day_number': 17, 'theme_category': 'Rewiring', 'theme_title': 'Choosing Self-Worth', 'theme_intention': 'I inherently deserve love and respect.', 'healing_focus': ['self-worth', 'value']}, {'day_number': 18, 'theme_category': 'Rewiring', 'theme_title': 'Boundaries as Love', 'theme_intention': 'I protect my energy with clear boundaries.', 'healing_focus': ['boundaries', 'self-respect']}, {'day_number': 19, 'theme_category': 'Rewiring', 'theme_title': 'The Voice of Kindness', 'theme_intention': 'I speak to myself as I would a dear friend.', 'healing_focus': ['self-talk', 'kindness']}, {'day_number': 20, 'theme_category': 'Rewiring', 'theme_title': 'Planting Seeds of Joy', 'theme_intention': 'I intentionally invite joy into my life.', 'healing_focus': ['joy', 'intention']}, {'day_number': 21, 'theme_category': 'Embodiment', 'theme_title': 'Living the Truth', 'theme_intention': 'I align my actions with my new beliefs.', 'healing_focus': ['alignment', 'action']}, {'day_number': 22, 'theme_category': 'Embodiment', 'theme_title': 'Stepping Into Power', 'theme_intention': 'I own my strength without apology.', 'healing_focus': ['personal power', 'confidence']}, {'day_number': 23, 'theme_category': 'Embodiment', 'theme_title': 'Authentic Connection', 'theme_intention': 'I bring my true self to my relationships.', 'healing_focus': ['authenticity', 'vulnerability']}, {'day_number': 24, 'theme_category': 'Embodiment', 'theme_title': 'Radiating Peace', 'theme_intention': 'My inner calm influences my outer world.', 'healing_focus': ['radiance', 'peace']}, {'day_number': 25, 'theme_category': 'Embodiment', 'theme_title': 'The Healed Self', 'theme_intention': 'I am embodying the person I came here to be.', 'healing_focus': ['embodiment', 'wholeness']}, {'day_number': 26, 'theme_category': 'Integration', 'theme_title': 'Weaving it Together', 'theme_intention': 'I integrate my lessons into my daily life.', 'healing_focus': ['integration', 'synthesis']}, {'day_number': 27, 'theme_category': 'Integration', 'theme_title': 'Embracing the Journey', 'theme_intention': 'I honor every step that brought me here.', 'healing_focus': ['reflection', 'honor']}, {'day_number': 28, 'theme_category': 'Integration', 'theme_title': 'Sustaining the Light', 'theme_intention': 'I am committed to my ongoing healing.', 'healing_focus': ['sustainability', 'commitment']}, {'day_number': 29, 'theme_category': 'Integration', 'theme_title': 'A Vision for the Future', 'theme_intention': 'I look forward with clarity and hope.', 'healing_focus': ['vision', 'hope']}, {'day_number': 30, 'theme_category': 'Integration', 'theme_title': 'Arrival', 'theme_intention': 'I am home within myself.', 'healing_focus': ['wholeness', 'completion']}]

def get_fallback_healing_plan():
    import copy
    return copy.deepcopy(FALLBACK_HEALING_PROFILE), copy.deepcopy(FALLBACK_THEMES)
