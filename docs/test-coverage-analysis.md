# Test Coverage Analysis

**Date:** 2026-03-15
**Overall line coverage:** 41% (1366 of 2303 lines uncovered)
**Tests:** 154 passing, 11 failing, 5 files with import errors
**Test files:** 37 | **Source files:** ~55 (excluding `__init__.py`)

---

## Current State

### What's well tested (>80% coverage)

| Module | Coverage | Notes |
|--------|----------|-------|
| `services/conversation.py` | 95% | Store/load history, user context |
| `services/postcode.py` | 98% | Postcode lookup and region mapping |
| `services/weather.py` | 98% | Forecast, frost risk, watering guidance |
| `services/engagement.py` | 90% | Quiet hours, sporadic send logic |
| `services/growing_plan.py` | 100% | Timing check and prioritisation |
| `services/milestone_checker.py` | 100% | Due milestone detection |
| `services/soil.py` | 82% | Soil profile lookups |
| `agents/orchestrator.py` | ~90% | Tool-use loop, system prompt |
| `data/seed_plants.py` | 84% | Plant seed data validation |
| All models | 100% | (declarative — imported, not logic-tested) |

### What's untested (0% coverage)

| Module | Lines | Priority | Why it matters |
|--------|-------|----------|----------------|
| `tasks/proactive_scheduler.py` | 96 | **HIGH** | Core engagement loop — sends proactive messages to all users |
| `tasks/weather_logger.py` | 32 | **HIGH** | Daily cron job, data integrity for weather history |
| `tasks/send_message.py` | 40 | **HIGH** | Outbound message delivery (WhatsApp) |
| `tasks/alert_scheduler.py` | 35 | **HIGH** | Alert evaluation and dispatch |
| `tasks/worker.py` | 24 | MEDIUM | ARQ worker config (mostly declarative) |
| `services/alerts.py` | 106 | **HIGH** | Alert creation, scheduling, deduplication |
| `agents/tools.py` | — | LOW | Static tool definitions (data, not logic) |
| `agents/system_prompt.py` | — | LOW | Template string (tested indirectly via orchestrator) |
| `channels/slack.py` | all | MEDIUM | Slack message handling, history merge logic |
| `api/whatsapp.py` | most | MEDIUM | Webhook endpoint (partially tested via webhook tests) |
| `main.py` | 19 | LOW | FastAPI app setup (lifespan) |
| `cli.py` | all | LOW | Interactive CLI — hard to unit test |
| `eval/*` | 429 | LOW | Evaluation framework — not production code |

---

## Recommended Improvements (Priority Order)

### 1. `services/alerts.py` — 0% coverage, 106 lines

**Risk:** Alert scheduling, deduplication, and dispatch is critical user-facing functionality with zero tests.

**Tests to add:**
- Alert creation with correct priority/type
- Deduplication: same alert not created twice for same user/plant/day
- Scheduling: alerts created with correct `scheduled_for` times
- Alert dispatch: pending alerts picked up and sent
- Edge cases: user with no plants, user with no location

### 2. `tasks/proactive_scheduler.py` — 0% coverage, 96 lines

**Risk:** This is the main engagement engine. Bugs here either spam users or silently stop outreach.

**Tests to add:**
- Quiet hours respected (no messages sent during quiet period)
- Frost alert triggers outbound message
- Milestone triggers included in message context
- Users with `notification_level="alerts_only"` only get urgent messages
- Sporadic send logic correctly evaluated
- No message sent when no triggers fire
- `last_sage_initiated_at` updated after send

### 3. `tasks/send_message.py` — 0% coverage, 40 lines

**Risk:** Outbound delivery path — if broken, users get no messages at all.

**Tests to add:**
- Text message dequeued and sent via WhatsApp API
- HTTP errors handled gracefully (retry vs. drop)
- Message status updated after successful send

### 4. `tasks/weather_logger.py` — 0% coverage, 32 lines

**Risk:** Data integrity — weather logs feed proactive alerts and historical analysis.

**Tests to add:**
- Idempotency: duplicate runs on same day don't create duplicate entries
- Handles weather API failures gracefully per-postcode
- All active postcodes are processed
- Empty user list handled correctly

### 5. `services/whatsapp.py` — 77% coverage, missing `download_media`

**Risk:** Media download is the path for photo analysis (plant ID, problem diagnosis).

**Tests to add:**
- `download_media` happy path (two-step: get URL, download content)
- `download_media` with failed URL lookup
- `download_media` with failed content download

### 6. `channels/slack.py` — 0% coverage

**Risk:** History merge logic (`_load_history`) has subtle rules (merge consecutive same-role, trim leading assistant) that could easily regress.

**Tests to add:**
- `_load_history` merges consecutive same-role messages
- `_load_history` trims leading assistant messages
- `_load_history` filters empty/whitespace messages
- `_find_or_create_slack_user` creates user with correct defaults
- `_load_context` returns correct plant summary

### 7. Fix the 11 failing tests

The failing tests in `test_integration.py` and `test_process_message.py` appear to have stale mocks or import issues. These should be fixed before adding new tests — broken tests erode confidence in the suite.

### 8. `services/onboarding.py` — 77% coverage

**Tests to add:**
- The uncovered branches (lines 121-127, 202-221, 263-265) likely represent edge cases in step transitions
- Error handling paths during onboarding

---

## Structural Improvements

### A. Add a `conftest.py` with shared fixtures

The current `conftest.py` only sets env vars. Common fixtures should be extracted:
- Mock Anthropic client
- Mock user/garden/plant factory functions
- Mock WhatsApp service
- In-memory SQLite session for service tests that need a database

### B. Separate unit tests from integration tests

Use pytest markers (`@pytest.mark.integration`) so fast unit tests can run independently of slower integration tests.

### C. Add coverage enforcement

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
addopts = "--cov=app --cov-fail-under=60"
```

This prevents coverage from regressing below a threshold as new code is added.

### D. Fix import errors in test collection

5 test files fail to collect due to `cryptography`/`redis` import issues in CI. These should either:
- Have their imports guarded
- Be marked with `pytest.importorskip("redis")`
- Have the environment fixed to include required native dependencies
