# 30-Day Healing Journey — API Documentation

**Base URL:** `{{base_url}}/api/healing`  
**Auth:** All endpoints require `Authorization: Bearer <token>` header.

---

## Day Lifecycle

Content generation is **strictly background-only**. No API call triggers AI generation.

| Time | Event |
|---|---|
| 6:00 PM (day before) | Background task pre-generates next day's content (state stays `locked`) |
| 12:00 AM (midnight) | Day unlocks → state becomes `available` |
| 11:59 PM (end of day) | If not completed → state becomes `missed` |

**Day states:** `locked` · `available` · `completed` · `missed`  
**Content statuses:** `pending` · `generating` · `ready` · `failed`

---

## 1. Assessment

### 1.1 Get Questions
**`GET /assessment/questions/`**

Returns the 10 onboarding questions with valid choices for dynamic UI rendering. No payload.

**Response (200 OK):**
```json
{
  "questions": [
    {
      "id": "q1_emotional_baseline",
      "type": "choice",
      "question": "How would you describe your baseline emotional state lately?",
      "options": ["Numb or disconnected", "Anxious or on edge", "Sad or emotionally heavy", "Angry or restless", "Lost or without direction", "Surprisingly okay"]
    },
    {
      "id": "q2_past_influence",
      "type": "scale",
      "question": "On a scale of 1-5, how much do you feel past experiences are influencing your present reactions?",
      "min": 1,
      "max": 5
    },
    {
      "id": "q3_life_area_impact",
      "type": "choice",
      "question": "Which area of your life feels the most impacted right now?",
      "options": ["Relationships & connection", "Self-worth & identity", "Career & purpose", "Body & physical health", "Family & belonging", "Inner peace & mental calm"]
    },
    {
      "id": "q4_core_pain_source",
      "type": "choice",
      "question": "When you feel most activated or in pain, what does it usually stem from?",
      "options": ["Feeling ignored, unseen, or emotionally neglected", "Being rejected or abandoned", "Being criticized, judged, or not good enough", "Feeling controlled, pressured, or powerless", "I don't fully know — just that something feels off"]
    },
    {
      "id": "q5_coping_pattern",
      "type": "choice",
      "question": "When things get heavy, what is your default coping mechanism?",
      "options": ["Withdraw from people", "Overwork or stay constantly busy", "Distract myself (phone, content, etc.)", "Overeat or lose appetite", "Seek comfort from someone", "Sit with it quietly"]
    },
    {
      "id": "q6_relationship_fear",
      "type": "choice",
      "question": "In relationships, what is your deepest fear?",
      "options": ["Being abandoned or left", "Being misunderstood", "Being controlled or losing independence", "Not being valued or chosen", "Getting too close to someone"]
    },
    {
      "id": "q7_core_belief",
      "type": "choice",
      "question": "If you had to guess, what is the core negative belief you hold about yourself?",
      "options": ["I am not enough", "No one truly stays", "I have to earn love", "The world doesn't feel safe", "I am broken beyond repair", "I don't know who I am"]
    },
    {
      "id": "q8_desired_relief",
      "type": "choice",
      "question": "What are you most tired of carrying?",
      "options": ["Overthinking", "Emotional pain", "Loneliness", "Lack of direction", "Self-doubt", "Feeling stuck"]
    },
    {
      "id": "q9_healing_resistance",
      "type": "choice",
      "question": "What has been your biggest block to healing so far?",
      "options": ["I didn't know where to start", "Fear of what I might uncover", "It felt selfish to focus on myself", "Lack of time or support", "I didn't believe I could change", "I tried before and it didn't work"]
    },
    {
      "id": "q10_personal_desire",
      "type": "text",
      "question": "If you could change one thing about how you feel every day, what would it be?",
      "placeholder": "Type your answer here..."
    }
  ]
}
```

---

### 1.2 Submit Assessment
**`POST /assessment/`**

Submits the 10-question assessment and triggers background plan generation. Send the user's IANA timezone via header so unlock dates are calculated in their local time.

**Header:** `X-User-Timezone: America/New_York` _(optional, defaults to UTC)_

**Payload:**
```json
{
  "q1_emotional_baseline": "Anxious or on edge",
  "q2_past_influence": 4,
  "q3_life_area_impact": "Self-worth & identity",
  "q4_core_pain_source": "Being rejected or abandoned",
  "q5_coping_pattern": "Withdraw from people",
  "q6_relationship_fear": "Being abandoned or left",
  "q7_core_belief": "I am not enough",
  "q8_desired_relief": "Emotional pain",
  "q9_healing_resistance": "Fear of what I might uncover",
  "q10_personal_desire": "I want to feel at peace with myself."
}
```

**Response (202 Accepted):** _(plan generation queued)_
```json
{
  "message": "Your healing journey is being created...",
  "assessment_id": 12,
  "status": "generating"
}
```

**Guard responses:**

| Condition | Status | Body |
|---|---|---|
| Journey already active | 409 Conflict | `{"error": "active_journey_exists", "message": "Your journey is already active."}` |
| Generation already in progress | 202 Accepted | `{"message": "Your healing journey is being created...", "status": "pending"}` |
| Previous attempt failed | 202 Accepted | Re-triggers generation: `{"message": "Retrying your journey creation...", "status": "generating"}` |

---

### 1.3 Poll Assessment Status
**`GET /assessment/status/`**

Poll every 3 seconds until `status` is `ready` or `failed`.

**Response (200 OK):**
```json
{
  "status": "ready",
  "day_1_unlocked": true,
  "journey_started_at": "2026-04-27T10:03:14Z"
}
```

`status` values: `pending` · `generating` · `ready` · `failed`

---

### 1.4 Get Healing Profile
**`GET /assessment/profile/`**

Returns the AI-generated healing profile and journey metadata.

**Response (200 OK):**
```json
{
  "healing_profile": {
    "healing_arc_summary": "...",
    "core_wound": "...",
    "primary_theme": "...",
    "archetype": "..."
  },
  "status": "ready",
  "journey_started_at": "2026-04-27T10:03:14Z",
  "journey_completed_at": null
}
```

---

## 2. Today's Day

### 2.1 Get Today
**`GET /today/`**

Returns the current active day. Always returns a meaningful state. Automatically syncs day states (unlocks/marks missed) on every call.

**Response — active day (200 OK):**
```json
{
  "day_number": 4,
  "state": "available",
  "content_status": "ready",
  "unlock_date": "2026-04-30",
  "completed_at": null,
  "theme": {
    "theme_title": "Reclaiming Inner Safety",
    "theme_intention": "To begin feeling at home in your own body.",
    "theme_category": "Foundation",
    "healing_focus": ["grounding", "self-compassion"]
  },
  "content": {
    "guided_reflection": "...",
    "affirmation": "I am safe to inhabit my body exactly as it is right now.",
    "mental_workout": "...",
    "physical_workout": {
      "title": "Grounding Stomp",
      "instructions": "...",
      "duration_seconds": 120
    },
    "breathing_exercise": {
      "name": "Box Breathing",
      "description": "...",
      "inhale_seconds": 4,
      "hold_in_seconds": 4,
      "exhale_seconds": 4,
      "hold_out_seconds": 4,
      "rounds": 4
    },
    "mini_challenge": "...",
    "journal_prompt": "...",
    "is_fallback": false,
    "generated_at": "2026-04-29T18:10:00Z"
  }
}
```

**State responses:**

| Condition | Body |
|---|---|
| No journey started | `{"state": "no_plan", "message": "..."}` |
| Plan generating | `{"state": "generating", "message": "..."}` |
| Plan generation failed | `{"state": "failed", "message": "..."}` |
| All 30 days completed | `{"state": "journey_complete", "message": "...", "journey_completed_at": "..."}` |

> If the current day's content is still being prepared (`content_status: pending/generating`), the response will include the day fields but `content` will be `null`.

---

## 3. Day Detail

### 3.1 Get Day by Number
**`GET /days/<day_number>/`**

Returns full content for a specific day. Day must be `available`, `missed`, or `completed`. Content is **never** triggered by this call — it is generated in the background.

**Response (200 OK):** _(same shape as `/today/` response above)_

**Error responses:**

| Condition | Status | Body |
|---|---|---|
| day_number < 1 or > 30 | 404 | `{"error": "Day N does not exist. Valid range: 1–30."}` |
| No journey found | 404 | `{"error": "No healing journey found. Please start your journey first."}` |
| Day is locked | 403 | `{"error": "day_locked", "message": "Day N is locked. It unlocks on YYYY-MM-DD.", "unlock_date": "YYYY-MM-DD"}` |
| Content pending/generating | 202 | `{"message": "Your day's content is being prepared...", "day_number": N, "content_status": "pending", "state": "available"}` |

---

## 4. 30-Day Plan Overview

### 4.1 Get Plan
**`GET /plan/`**

Returns the full 30-day grid — lightweight, no content modules. Includes the healing arc summary and per-day state.

**Response (200 OK):**
```json
{
  "healing_arc_summary": "Your journey begins by...",
  "themes": [
    {
      "day_number": 1,
      "theme_title": "Meeting the Wound",
      "theme_intention": "To gently acknowledge what is hurting.",
      "theme_category": "Foundation",
      "healing_focus": ["self-awareness", "acceptance"],
      "state": "missed",
      "unlock_date": "2026-04-27",
      "completed_at": null
    },
    {
      "day_number": 4,
      "theme_title": "Reclaiming Inner Safety",
      "theme_intention": "To begin feeling at home in your own body.",
      "theme_category": "Foundation",
      "healing_focus": ["grounding", "self-compassion"],
      "state": "available",
      "unlock_date": "2026-04-30",
      "completed_at": null
    }
  ]
}
```

`theme_category` values: `Foundation` · `Awareness` · `Release` · `Rewiring` · `Embodiment` · `Integration`

---

## 5. Complete a Day

### 5.1 Mark Day Complete
**`POST /days/<day_number>/complete/`**

Marks a day as completed. Idempotent — safe to call twice. Updates streak, recovers grace period if active, detects milestones, and marks journey complete on Day 30. Both fields are optional.

**Payload:**
```json
{
  "mood": "happy",
  "journal_entry_id": 42
}
```

`mood` valid values: `happy` · `fear` · `sad` · `angry` · `sick`

**Response (200 OK):**
```json
{
  "message": "Day 4 complete.",
  "current_streak": 1,
  "total_days_completed": 1,
  "milestone_reached": null
}
```

**Milestone response example:**
```json
{
  "message": "Day 7 complete.",
  "current_streak": 7,
  "total_days_completed": 7,
  "milestone_reached": {
    "day": 7,
    "message": "One full week. Your nervous system is changing."
  }
}
```

**Idempotent (already completed) response (200 OK):**
```json
{
  "message": "Day 4 was already completed.",
  "current_streak": 1,
  "already_completed": true
}
```

**Error responses:**

| Condition | Status | Body |
|---|---|---|
| Day is locked | 403 | `{"error": "day_locked", "message": "Day N is locked."}` |
| No journey found | 404 | `{"error": "No healing journey found."}` |

---

## 6. Mental Exercise Reflection

### 6.1 Save Reflection
**`POST /days/<day_number>/reflection/`**

Saves the user's written reflection from the mental workout exercise. Triggers a background task that extracts personal insights from the reflection and stores them in the user's AI memory for more personalized future interactions.

**Payload:**
```json
{
  "mentalreflectiontext": "I noticed that I tend to withdraw whenever I feel overwhelmed..."
}
```

**Response (201 Created):**
```json
{
  "id": 7,
  "healing_day": 42,
  "mentalreflectiontext": "I noticed that I tend to withdraw whenever I feel overwhelmed...",
  "created_at": "2026-04-30T10:15:00Z"
}
```

**Error (400):** `{"error": "mentalreflectiontext is required."}`  
**Error (404):** `{"error": "Healing day not found."}`

---

## 7. Progress & Streak

### 7.1 Get Progress
**`GET /progress/`**

Returns streak data, milestones, and grace period status.

**Response (200 OK):**
```json
{
  "total_days_completed": 5,
  "current_streak": 3,
  "longest_streak": 5,
  "milestones_reached": [3],
  "grace_period_active": false,
  "grace_expires_at": null,
  "journey_complete": false,
  "journey_started_at": "2026-04-27T10:03:14Z",
  "journey_completed_at": null
}
```

**Grace period:** When a user misses a day, `grace_period_active` becomes `true` and they have until `grace_expires_at` (end of next local day) to complete the missed day without losing their streak. Completing any day during the grace window clears it.

---

## 8. Settings

### 8.1 Get Settings
**`GET /settings/`**

**Response (200 OK):**
```json
{
  "timezone": "America/New_York",
  "morning_reminder_enabled": true,
  "evening_reminder_enabled": true,
  "morning_reminder_time": "07:00:00",
  "evening_reminder_time": "20:00:00"
}
```

### 8.2 Update Settings
**`PATCH /settings/`**

All fields are optional. Timezone must be a valid IANA string (e.g., `America/New_York`, `Asia/Dhaka`).

**Payload:**
```json
{
  "morning_reminder_enabled": false,
  "morning_reminder_time": "08:30:00",
  "timezone": "America/New_York"
}
```

**Response (200 OK):** Updated settings object _(same shape as GET)_

**Error (400):** `{"timezone": ["'Bad/Zone' is not a valid timezone."]}`

---

## 9. Affirmations

### 9.1 Save Day Affirmation
**`POST /days/<day_number>/save-affirmation/`**

Saves the affirmation from a specific day to the user's favorites. Protected against duplicates.

**Payload:** `{}`

**Response (201 Created):**
```json
{
  "message": "Affirmation saved successfully."
}
```

**Response (200 OK):** _(duplicate — already saved)_
```json
{
  "message": "Affirmation already saved."
}
```

**Error (404):** `{"error": "Content not found for this day."}`

---

### 9.2 List Saved Affirmations
**`GET /affirmations/`**

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "text": "I am safe to inhabit my body exactly as it is right now.",
    "day_number": 4,
    "created_at": "2026-04-30T10:00:00Z"
  }
]
```

---

### 9.3 Delete Saved Affirmation
**`DELETE /affirmations/<pk>/`**

**Response (204 No Content)**

**Error (404):** `{"error": "Affirmation not found."}`

---

## 10. Community Sharing

### 10.1 Share to Community
**`POST /days/<day_number>/share/`**

Shares the day's affirmation or linked journal entry to the community feed as a new post.

**Payload:**
```json
{
  "type": "affirmation"
}
```

`type` values: `affirmation` · `journal`

**Response (201 Created):**
```json
{
  "message": "Shared to community successfully."
}
```

**Error responses:**

| Condition | Status | Body |
|---|---|---|
| Healing day not found | 404 | `{"error": "Healing day not found."}` |
| No affirmation content | 404 | `{"error": "Affirmation not found for this day."}` |
| No journal entry linked | 404 | `{"error": "Journal entry not linked to this day."}` |
| Internal error | 500 | `{"error": "Failed to share."}` |

---

## 11. Reset Journey

### 11.1 Reset
**`POST /reset/`**

Archives the current journey and resets the streak to zero. Settings (timezone + reminder preferences) are preserved. The user is returned to the onboarding flow.

**Payload:** `{}`

**Response (200 OK):**
```json
{
  "message": "Your previous journey has been archived. Start your new journey when you're ready.",
  "archived_journey_id": 12
}
```

**Error (404):** `{"error": "no_active_journey", "message": "No active journey to reset."}`

---

## Endpoint Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/assessment/questions/` | Get the 10 onboarding questions |
| POST | `/assessment/` | Submit assessment & start plan generation |
| GET | `/assessment/status/` | Poll plan generation status |
| GET | `/assessment/profile/` | Get AI-generated healing profile |
| GET | `/today/` | Get today's active day |
| GET | `/days/<day_number>/` | Get a specific day's content |
| POST | `/days/<day_number>/complete/` | Mark a day as completed |
| POST | `/days/<day_number>/reflection/` | Save mental exercise reflection |
| POST | `/days/<day_number>/save-affirmation/` | Save day's affirmation to favorites |
| POST | `/days/<day_number>/share/` | Share to community feed |
| GET | `/plan/` | Get the full 30-day plan overview |
| GET | `/progress/` | Get streak & progress data |
| GET | `/settings/` | Get reminder settings |
| PATCH | `/settings/` | Update reminder settings |
| GET | `/affirmations/` | List saved affirmations |
| DELETE | `/affirmations/<pk>/` | Delete a saved affirmation |
| POST | `/reset/` | Archive journey & reset |
