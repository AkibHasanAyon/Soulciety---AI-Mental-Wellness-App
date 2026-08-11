# 30-Day Healing Journey — Development TODO Tracker

**Last Updated:** April 23, 2026  
**Status Legend:** `[ ]` Not started · `[/]` In progress · `[x]` Completed

---

## Phase 1: Foundation — Models & Migrations ✅

- [x] Create `healing_journey` Django app (`startapp`)
- [x] Add `healing_journey` to `INSTALLED_APPS`
- [x] Register URL prefix in `tlecap_backend/urls.py`
- [x] **Models** (`models.py`)
  - [x] `HealingAssessment` model (FK user, 10 answer fields, status, `is_archived`, lifecycle timestamps)
  - [x] `HealingJourneySettings` model (OneToOne user, timezone, reminder prefs)
  - [x] `HealingTheme` model (FK assessment, day_number, title, intention, category, focus)
  - [x] `HealingDay` model (FK user + theme, state, content_status, unlock_date, FK mood/journal)
  - [x] `DayContent` model (OneToOne HealingDay, 7 content modules, is_fallback)
  - [x] `HealingStreak` model (OneToOne user, streak fields, grace period, milestones)
- [x] Create and run database migrations
- [x] **Admin panel** (`admin.py`)
  - [x] `HealingAssessment` admin (list/filter/retry action)
  - [x] `HealingJourneySettings` admin
  - [x] `HealingTheme` admin (read-only)
  - [x] `HealingDay` admin (list/filter)
  - [x] `DayContent` admin (read-only)
  - [x] `HealingStreak` admin
- [x] Create placeholder files (`serializers.py`, `views.py`, `urls.py`, `tasks.py`, `prompts.py`, `fallbacks.py`, `validators.py`)
- [x] **Tests** (37 tests — all passing ✅)
  - [x] Model creation tests
  - [x] Field constraint tests
  - [x] FK relationship tests
  - [x] `python manage.py check` passes
  - [x] `python manage.py migrate --check` passes

---

## Phase 2: Assessment — Onboarding API ✅

- [x] **Serializers** (`serializers.py`)
  - [x] `AssessmentSubmissionSerializer` (validate 10 answers with strict MCQ ChoiceField)
  - [x] `AssessmentStatusSerializer`
  - [x] `HealingProfileSerializer`
- [x] **Views** (`views.py`)
  - [x] `POST /api/healing/assessment/` — submit assessment
  - [x] Re-submission guard logic (409 / 202 / allow re-submit)
  - [x] Extract `X-User-Timezone` header
  - [x] `GET /api/healing/assessment/status/` — poll generation status
  - [x] `GET /api/healing/assessment/profile/` — retrieve healing profile
- [x] **URLs** (`urls.py`)
  - [x] Wire 3 assessment endpoints
- [x] **Input validation**
  - [x] Validate Q1–Q9 against allowed MCQ options (ChoiceField with exact option lists)
  - [x] Validate Q2 range (1–5) (IntegerField with min/max)
  - [x] Validate Q10 max length (500 chars) and min length (1)
- [x] **Tests** (73 total — 37 model + 36 API — all passing ✅)
  - [x] Valid submission returns 202
  - [x] Invalid answers rejected (all Q1–Q9 MCQ + Q10 length)
  - [x] Duplicate submission returns 409
  - [x] Re-submission after failure returns 202
  - [x] Race condition guard (pending/generating → 202)
  - [x] Status polling returns correct status (all 4 states)
  - [x] Profile retrieval 200 / 404
  - [x] Auth required (401 without JWT)
  - [x] Archived journey doesn't block new submission
  - [x] All Q1 and Q7 option exhaustive acceptance tests

---

## Phase 3: AI Integration — Plan Generation ✅

- [x] **Prompts** (`prompts.py`)
  - [x] `PLAN_GENERATION_SYSTEM_PROMPT` (trauma-informed, 6-phase arc, JSON-only output)
  - [x] `PLAN_GENERATION_USER_PROMPT_TEMPLATE` + `build_plan_generation_prompt()` helper
  - [x] `CONTENT_GENERATION_SYSTEM_PROMPT` + `CONTENT_GENERATION_USER_PROMPT_TEMPLATE` (Phase 4 ready)
- [x] **Validators** (`validators.py`)
  - [x] `validate_healing_profile(data)` — 10 required keys, non-empty check
  - [x] `validate_themes(themes)` — exact 30, sequential, valid categories, non-empty focus
  - [x] `validate_plan_response(data)` — top-level wrapper
  - [x] `validate_breathing_exercise(data)` — integer range checks (Phase 4 ready)
  - [x] `validate_day_content(data)` — 7 modules, non-empty text (Phase 4 ready)
- [x] **Gemini client utility**
  - [x] Lazy-init `_get_gemini_client()` with reuse across task invocations
  - [x] `_parse_json_response()` with markdown fence stripping
- [x] **Celery Task: `generate_healing_plan`** (`tasks.py`)
  - [x] Status → `generating`
  - [x] Build prompt from assessment answers
  - [x] Call Gemini `gemini-2.5-flash` (max_tokens=4000, temp=0.8)
  - [x] Parse JSON response (handles markdown fences)
  - [x] Validate response (profile + themes)
  - [x] Save healing profile to assessment
  - [x] Set `journey_started_at`
  - [x] Atomic creation: 30 themes + 30 days + streak + settings
  - [x] Pre-calculate 30 `unlock_date` values (Day 1 = available, rest = locked)
  - [x] Status → `ready`
  - [x] Day 1 content trigger stub (Phase 4)
  - [x] Push + in-app notification via notifications.helpers
  - [x] Failure handling (3 retries, 60s backoff)
  - [x] Store error in `generation_error` on permanent failure
  - [x] `_mark_plan_failed()` helper with failure notification
- [x] Wire `transaction.on_commit()` in assessment view (both new + re-submission paths)
- [x] **Tests** (122 total — 37 model + 36 API + 49 Phase 3 — all passing ✅)
  - [x] Prompt construction with all 10 answers
  - [x] Profile validation (valid + invalid: missing keys, empty values, wrong type)
  - [x] Theme validation (valid + edge cases: wrong count, duplicates, invalid category, missing keys)
  - [x] Full task flow (mocked Gemini) — verify 30 themes + 30 days created
  - [x] Atomic record creation verification (streak, settings, unlock dates)
  - [x] Status transition lifecycle (generating → ready)
  - [x] Retry behavior (empty response, invalid JSON, schema validation)
  - [x] Permanent failure after max retries
  - [x] JSON parsing (plain, markdown-fenced, whitespace)
  - [x] Breathing exercise boundary validation
  - [x] Day content validation (7 modules, empty/whitespace checks)

---

## Phase 4: Daily Content Engine ✅

- [x] **Prompts** (`prompts.py`)
  - [x] `CONTENT_GENERATION_SYSTEM_PROMPT` — trauma-informed, 7-module JSON format
  - [x] `CONTENT_GENERATION_USER_PROMPT_TEMPLATE` + `build_content_generation_prompt()` helper
- [x] **Validators** (`validators.py`) — already implemented in Phase 3
  - [x] `validate_day_content(data)` — 7 required modules, non-empty checks
  - [x] `validate_breathing_exercise(data)` — integer range checks
- [x] **Fallback content** (`fallbacks.py`)
  - [x] `FALLBACK_CONTENT_BANK` — Foundation phase (grounding, safety)
  - [x] `FALLBACK_CONTENT_BANK` — Awareness phase (patterns, observation)
  - [x] `FALLBACK_CONTENT_BANK` — Release phase (letting go, forgiveness)
  - [x] `FALLBACK_CONTENT_BANK` — Rewiring phase (new beliefs, identity)
  - [x] `FALLBACK_CONTENT_BANK` — Embodiment phase (living new self)
  - [x] `FALLBACK_CONTENT_BANK` — Integration phase (wholeness, closing loop)
  - [x] `get_fallback_content()` helper with category lookup
- [x] **Celery Task: `generate_day_content`** (`tasks.py`)
  - [x] Set `content_status → 'generating'`
  - [x] Guard: skip if content already exists
  - [x] Build prompt from theme + profile via `build_content_generation_prompt()`
  - [x] Call Gemini `gemini-2.5-flash` (max_tokens=4500, temp=0.9)
  - [x] Parse + validate JSON (7 modules + breathing exercise)
  - [x] Create `DayContent` record with `is_fallback=False`
  - [x] Set `content_status → 'ready'`
  - [x] Failure → `_handle_content_failure()` → `serve_fallback_content.delay()`
  - [x] 3 retries, 30s backoff
- [x] **Celery Task: `generate_day_content_batch`** (`tasks.py`)
  - [x] Find tomorrow's pending days (`unlock_date=tomorrow, content_status='pending', state='locked'`)
  - [x] Dispatch individual `generate_day_content` tasks
  - [x] Ready for Celery Beat registration (6 AM UTC)
- [x] **Celery Task: `serve_fallback_content`** (`tasks.py`)
  - [x] Select by `theme_category` from `FALLBACK_CONTENT_BANK`
  - [x] Guard: don't overwrite existing content
  - [x] Create `DayContent` with `is_fallback=True`
  - [x] Set `content_status → 'ready'`
  - [x] Log fallback event
- [x] **API: `GET /api/healing/days/<day_number>/`** (`views.py`)
  - [x] Return full day + content (200) when `content_status='ready'`
  - [x] On-demand trigger for pending content (202)
  - [x] Polling message for generating/failed content (202)
  - [x] 403 for locked days + unlock_date info
  - [x] 404 for out of range or no journey
- [x] **Serializers** (`serializers.py`)
  - [x] `DayDetailSerializer` (theme + content + state)
  - [x] `DayContentSerializer` (7 modules + is_fallback + generated_at)
  - [x] `ThemeSerializer` (title, intention, category, focus)
  - [x] `BreathingExerciseSerializer` (structured JSON fields)
- [x] **URL** (`urls.py`)
  - [x] `path('days/<int:day_number>/', ...)` → activated
- [x] **Day 1 trigger** wired in `generate_healing_plan` (replaced Phase 3 TODO stub)
- [x] **Tests** (151 total — all passing ✅)
  - [x] Content generation happy-path (mocked AI)
  - [x] Content generation skip guard (existing content)
  - [x] Content generation not-found handling
  - [x] Content generation retry behavior (empty response)
  - [x] Permanent failure triggers fallback queue
  - [x] Content prompt construction (day_number, theme, trauma_type, healing_focus)
  - [x] Content system prompt validation
  - [x] Fallback bank completeness (all 6 phases × 7 modules)
  - [x] Fallback breathing exercises pass validation
  - [x] Fallback creates DayContent with is_fallback=True
  - [x] Fallback does not overwrite existing content
  - [x] Fallback works for each of the 6 categories
  - [x] Batch finds tomorrow's pending days correctly
  - [x] Batch ignores already-ready content
  - [x] Day detail API: ready → 200 with full content
  - [x] Day detail API: locked → 403
  - [x] Day detail API: out of range → 404
  - [x] Day detail API: no journey → 404
  - [x] Day detail API: pending → 202 + on-demand trigger
  - [x] Day detail API: generating → 202 polling
  - [x] Day detail API: unauthenticated → 401

---

## Phase 5: Day Lifecycle & Unlock System ✅

- [x] **Celery Task: `unlock_healing_days`** (`tasks.py`)
  - [x] Fetch all locked days with `select_related('user')`
  - [x] Cache user timezone lookups to avoid repeated queries
  - [x] Convert UTC to user's local time via `zoneinfo.ZoneInfo`
  - [x] Transition `locked → available` when `local_date >= unlock_date`
  - [x] Fallback to UTC when `HealingJourneySettings` missing
  - [x] Ready for Celery Beat registration (hourly, `0 * * * *`)
- [x] **API: `GET /api/healing/today/`** (`views.py` → `TodayView`)
  - [x] `no_plan` state — no assessment exists
  - [x] `generating` state — plan being created
  - [x] `failed` state — plan generation failed
  - [x] `journey_complete` state — all 30 days done
  - [x] Available day — returns full day detail via `DayDetailSerializer`
  - [x] Skips completed days, returns lowest uncompleted available day
  - [x] Falls back to last completed day if all available are completed
- [x] **API: `GET /api/healing/plan/`** (`views.py` → `PlanOverviewView`)
  - [x] Returns `healing_arc_summary` + `themes[]` array (30 items)
  - [x] Each theme includes: day_number, title, intention, category, focus, state, unlock_date
  - [x] 404 if no plan or plan not ready
- [x] **Past day read-only access**
  - [x] Completed days viewable (200) with full content
  - [x] Missed days viewable (200) with content
  - [x] Locked days return 403 (not viewable)
- [x] **Serializers** (`serializers.py`)
  - [x] `PlanDaySerializer` — lightweight theme+state for grid UI (no full content)
- [x] **URLs** (`urls.py`)
  - [x] `path('plan/', ...)` → activated
  - [x] `path('today/', ...)` → activated
- [x] **Tests** (172 total — all passing ✅, 21 new Phase 5 tests)
  - [x] Unlock: local date reached → available
  - [x] Unlock: future date stays locked
  - [x] Unlock: today's date unlocks
  - [x] Unlock: skips already-available days
  - [x] Unlock: multi-user timezone behavior
  - [x] Unlock: UTC fallback when no settings
  - [x] Unlock: multiple days at once
  - [x] Today: no_plan state
  - [x] Today: generating state
  - [x] Today: failed state
  - [x] Today: journey_complete state
  - [x] Today: available day returned with content
  - [x] Today: skips completed days
  - [x] Today: unauthenticated → 401
  - [x] Plan: no plan → 404
  - [x] Plan: not ready → 404
  - [x] Plan: 30 themes with state
  - [x] Plan: completed day state reflected
  - [x] Plan: unauthenticated → 401
  - [x] Past day: completed day viewable
  - [x] Past day: missed day viewable

---

## Phase 6: Progress, Streaks & Milestones ✅

- [x] **API: `POST /api/healing/days/<day_number>/complete/`** (`views.py` → `DayCompleteView`)
  - [x] Accept optional `mood` + `journal_entry_id`
  - [x] Idempotency guard — returns `already_completed=true` without double-counting
  - [x] State transitions: `available → completed`, `missed → completed` (grace recovery)
  - [x] Create `MoodEntry` via `app_home.models.MoodEntry`, link to `HealingDay`
  - [x] Link `JournalEntry` by ID, with ownership check
  - [x] Guard: locked days → 403, invalid mood → 400, missing journey → 404
- [x] **Streak update logic** (in `DayCompleteView.post`)
  - [x] Increment `current_streak` + `total_days_completed`
  - [x] Update `longest_streak` when surpassed
  - [x] Set `last_completed_date`
  - [x] Grace period recovery on completion (clears `grace_period_active + grace_expires_at`)
- [x] **Celery Task: `check_missed_days_and_streaks`** (`tasks.py`)
  - [x] Mark `available → missed` when user's local date > unlock_date
  - [x] Grace period activation (first miss → 24h grace window)
  - [x] Grace period preservation (within window → streak preserved)
  - [x] Grace period expiry (expired → streak zeroed)
  - [x] Timezone-aware with user setting cache
  - [x] Ready for Celery Beat registration (hourly, `0 * * * *`)
- [x] **Milestone detection** (in `DayCompleteView.post`)
  - [x] Milestones at days 3, 7, 14, 21, 30
  - [x] Idempotency (skip if already in `milestones_reached[]`)
  - [x] Updates `milestones_reached` JSON array
  - [x] Sends in-app notification via `notifications.helpers.create_notification`
- [x] **Journey completion (Day 30)** (in `DayCompleteView.post`)
  - [x] Sets `journey_completed_at` on `HealingAssessment`
  - [x] Sends completion notification
  - [x] Day 30 milestone triggers alongside journey completion
- [x] **API: `GET /api/healing/progress/`** (`views.py` → `ProgressView`)
  - [x] Returns streak data, milestones, grace status
  - [x] Includes `journey_complete`, `journey_started_at`, `journey_completed_at`
  - [x] 404 if no streak exists
- [x] **Serializers** (`serializers.py`)
  - [x] `DayCompleteSerializer` — validates mood choices + journal_entry_id
  - [x] `ProgressSerializer` — full streak + journey metadata
- [x] **URLs** (`urls.py`)
  - [x] `path('days/<int:day_number>/complete/', ...)` → activated
  - [x] `path('progress/', ...)` → activated
- [x] **Tests** (199 total — all passing ✅, 27 new Phase 6 tests)
  - [x] Day completion: first time, idempotent, locked → 403
  - [x] Day completion: with mood, without mood, invalid mood → 400
  - [x] Day completion: missed day grace recovery
  - [x] Day completion: no journey → 404, unauthenticated → 401
  - [x] Streak math: increments, longest updates, last_completed_date set
  - [x] Milestones: day 3, day 7 triggers, idempotent skip
  - [x] Journey completion: Day 30 sets completed_at, streak=30, milestone=30
  - [x] Missed days: mark missed, grace activation, preservation, expiry
  - [x] Missed days: today not marked, completed not affected
  - [x] Progress: no streak → 404, data returned, journey_complete flag, 401

---

## Phase 7: Notifications & Reminders ✅

- [x] **New notification types** (updated `notifications/models.py`)
  - [x] `healing_plan_ready`
  - [x] `healing_day_available`
  - [x] `healing_evening_reminder`
  - [x] `healing_milestone`
  - [x] `healing_complete`
- [x] **Celery Task: `send_healing_reminders`** (`tasks.py`)
  - [x] Combined morning + evening into single hourly task
  - [x] Morning reminder: matches local hour to configured `morning_reminder_time`
  - [x] Evening reminder: matches local hour to configured `evening_reminder_time`
  - [x] Checks `morning_reminder_enabled` / `evening_reminder_enabled` per user
  - [x] Respects global `UserProfile.notifications_enabled`
  - [x] Skips users with completed journeys or no available day
  - [x] Ready for Celery Beat registration (hourly, `0 * * * *`)
- [x] **API: `GET /api/healing/settings/`** (`views.py` → `SettingsView`)
  - [x] Returns timezone, reminder preferences, reminder times
  - [x] 404 if no settings exist
- [x] **API: `PATCH /api/healing/settings/`** (`views.py` → `SettingsView`)
  - [x] Partial update: timezone, reminder toggles, reminder times
  - [x] Timezone validation via `zoneinfo.ZoneInfo`
  - [x] 400 for invalid timezone
- [x] **Hook notifications into tasks** (updated `DayCompleteView`)
  - [x] Milestone → `healing_milestone` notif type
  - [x] Journey complete → `healing_complete` notif type
- [x] **Serializers** (`serializers.py`)
  - [x] `SettingsSerializer` — timezone validation + reminder fields
- [x] **URLs** (`urls.py`)
  - [x] `path('settings/', ...)` → activated
- [x] **Tests** (213 total — all passing ✅, 14 new Phase 7 tests)
  - [x] Reminders: morning sent at configured time
  - [x] Reminders: evening sent at configured time
  - [x] Reminders: wrong hour → no reminders
  - [x] Reminders: disabled morning skips
  - [x] Reminders: no available day skips
  - [x] Reminders: completed journey skips
  - [x] Settings: GET returns current settings
  - [x] Settings: PATCH timezone
  - [x] Settings: PATCH reminder preferences
  - [x] Settings: invalid timezone → 400
  - [x] Settings: no settings → 404
  - [x] Settings: partial patch
  - [x] Settings: unauthenticated → 401
  - [x] Notification types: all 5 healing types registered

---

## Phase 8: Journey Reset & Edge Cases ✅

- [x] **API: `POST /api/healing/reset/`** (`views.py` → `ResetJourneyView`)
  - [x] Soft-archive assessment (`is_archived=True`)
  - [x] Atomic transaction for data safety
  - [x] Reset `HealingStreak` to defaults (zero counters, clear grace, clear milestones)
  - [x] Preserve `HealingJourneySettings` (timezone + reminder prefs carry over)
  - [x] Return `archived_journey_id` in response
  - [x] 404 if no active journey
- [x] **Assessment guard** (already implemented in Phase 2)
  - [x] Only checks non-archived assessments (`is_archived=False`)
- [x] **DayDetailView fix** — serve fallback content for `failed` days
  - [x] If `content_status='failed'` AND `DayContent` exists → serve with 200
  - [x] If `content_status='failed'` AND no content → 202 (still generating)
- [x] **Edge cases**
  - [x] Double-tap race condition on assessment POST → 202 (keep polling)
  - [x] Double-tap race condition on day complete → idempotent (no double-count)
  - [x] Timezone change mid-journey → settings update via PATCH
  - [x] On-demand content retry for failed days → fallback served
  - [x] Grace period recovery flow → full end-to-end tested
  - [x] Out-of-range day numbers → 404
  - [x] Double reset → 404 (already archived)
- [x] **URLs** (`urls.py`)
  - [x] `path('reset/', ...)` → activated
- [x] **Tests** (227 total — all passing ✅, 14 new Phase 8 tests)
  - [x] Reset: archives assessment, resets streak, preserves settings
  - [x] Reset: old data preserved (soft delete)
  - [x] Reset: can start new journey after reset
  - [x] Reset: no active journey → 404, double reset → 404
  - [x] Reset: unauthenticated → 401
  - [x] Edge: double-tap assessment → 202
  - [x] Edge: double-tap complete → idempotent
  - [x] Edge: timezone change mid-journey
  - [x] Edge: missed day grace recovery full flow
  - [x] Edge: out-of-range day → 404
  - [x] Edge: fallback content served on failed day

---

## Phase 9: Integration Testing & Polish ✅

- [x] **End-to-end journey simulation**
  - [x] Full 30-day lifecycle test (complete all days → milestones → journey_complete → progress + today verification)
  - [x] Journey then reset then restart test (complete 5 → reset → streak zeroed → new assessment accepted)
  - [x] Multi-user concurrent test (3 users at different progress levels, independent streaks)
  - [x] Multi-user reset isolation (resetting one user doesn't affect others)
  - [x] Multi-timezone unlock test (UTC/New_York/Tokyo users all get correct unlock behavior)
- [x] **Error response consistency**
  - [x] 401 across all 10 endpoints when unauthenticated
  - [x] 404 on journey-dependent endpoints when no journey exists
- [x] **Celery task monitoring**
  - [x] `unlock_healing_days` returns structured count string
  - [x] `check_missed_days_and_streaks` returns missed + grace expired counts
  - [x] `send_healing_reminders` returns morning + evening counts
  - [x] All tasks have comprehensive logging (`logger.info`, `logger.warning`)
- [x] **FK integrity verification**
  - [x] `HealingDay.mood_entry` FK → `app_home.MoodEntry` (with SET_NULL cascade)
  - [x] `HealingDay.journal_entry` FK → `journal.JournalEntry` (nullable)
  - [x] `HealingAssessment` cascade delete → themes + days cleaned up
- [x] **Code quality review**
  - [x] All TODO/FIXME markers cleared (0 remaining)
  - [x] Admin `retry_failed_plans` now triggers actual Celery task
  - [x] `python manage.py check` passes (0 issues)
- [x] **Migration verification**
  - [x] Generated `notifications` migration (new notification types)
  - [x] `python manage.py makemigrations --check --dry-run` — no pending changes
- [x] **DayDetailView enhanced** (Phase 8/9 overlap)
  - [x] Failed content with fallback → served as 200 (not 202)
  - [x] Generating content → 202 poll
  - [x] Failed with no content yet → 202 poll
- [x] **Tests** (240 total — all passing ✅, 13 new Phase 9 tests)
  - [x] E2E: full 30-day lifecycle with all milestones
  - [x] E2E: journey → reset → restart cycle
  - [x] Multi-user: independent progression (3 users)
  - [x] Multi-user: reset isolation
  - [x] Multi-timezone: unlock behavior across 3 timezones
  - [x] Consistency: 401 on all endpoints
  - [x] Consistency: 404 when no journey
  - [x] Celery: unlock task returns count
  - [x] Celery: missed task returns counts
  - [x] Celery: reminder task returns counts
  - [x] FK: mood_entry SET_NULL
  - [x] FK: journal_entry nullable
  - [x] FK: assessment cascade delete

---

## Summary

| Phase | Items | Status |
|-------|-------|--------|
| Phase 1: Foundation | 17 tasks | ✅ Complete |
| Phase 2: Assessment API | 18 tasks | ✅ Complete |
| Phase 3: AI Plan Generation | 22 tasks | ✅ Complete |
| Phase 4: Content Engine | 25 tasks | ✅ Complete |
| Phase 5: Day Lifecycle | 11 tasks | ✅ Complete |
| Phase 6: Streaks & Milestones | 20 tasks | ✅ Complete |
| Phase 7: Notifications | 14 tasks | ✅ Complete |
| Phase 8: Reset & Edge Cases | 12 tasks | ✅ Complete |
| Phase 9: Integration & Polish | 14 tasks | ✅ Complete |
| **Total** | **153 tasks** | **✅ All Complete** |
