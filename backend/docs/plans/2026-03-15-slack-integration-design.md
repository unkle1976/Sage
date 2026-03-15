# Slack Integration Design — Phase 1 (Test Harness)

**Date:** 2026-03-15
**Purpose:** Add Slack as a chat channel so Nick can test Sage from his phone via the Slack app, before WhatsApp goes live.

## Architecture

Slack Bot (Socket Mode) connects outbound from the laptop to Slack's servers via WebSocket. No public URL needed. Nick DMs the Sage bot in Slack, messages route through the same SageOrchestrator used by the CLI.

```
Phone (Slack app) → Slack servers → Socket Mode WebSocket → Laptop backend
    → SageOrchestrator → Claude API → response
    → PostgreSQL (conversation history, context events, plants)
    → Reply via Slack API → Phone
```

## What Changes

### New files
- `app/channels/slack.py` — Slack Bolt app with Socket Mode listener, message handler, onboarding routing
- `app/slack_bot.py` — Entry point (`python -m app.slack_bot`)

### Model changes
- `ConversationMessage` — add `channel` column (cli/slack/whatsapp), default "cli"
- `User` — add `slack_user_id` column for mapping Slack users to Sage users
- Alembic migration for both

### Config changes
- `app/core/config.py` — add `slack_bot_token` and `slack_app_token` settings
- `.env` — tokens already added

### Dependencies
- `slack-bolt` (includes `slack-sdk`)

## Message Flow

1. User sends DM to Sage bot in Slack
2. Slack Bolt listener receives the message event
3. Look up User by `slack_user_id` — create if new (onboarding_step="awaiting_first_plant")
4. If not onboarded: route through OnboardingService (same as CLI)
5. If onboarded: load context + history, route through SageOrchestrator
6. Store both user and assistant messages in ConversationMessage (channel="slack")
7. Reply in the same Slack DM

## Onboarding in Slack

Same 3-step flow as CLI:
1. Welcome message: "Hey! I'm Sage, your gardening mate. What are you thinking of growing?"
2. User says what they're planting → stored
3. "What's your postcode?" → soil/region lookup → done

## Not in Scope (Phase 1)
- Events API (needs public URL — Phase 2 when deployed)
- Multi-channel message routing via Redis queues
- Proactive messages via Slack (Phase 2)
- Web dashboard (separate design)

## How to Run
```bash
cd backend && source .venv/bin/activate
python -m app.slack_bot
```

## Phase 2 (Later)
- Deploy to server, switch to Events API
- Proactive messages via Slack
- Multi-channel: WhatsApp + Slack feeding same Redis queue
