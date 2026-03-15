# Automated Conversation Evaluation System

## Date: 2026-03-15

## Problem
Manual testing of Sage conversations takes ~25 minutes per test. We need to run 10-50 conversation tests in minutes, not hours.

## Architecture

Three components:

1. **Synthetic User** — Claude instance with a persona system prompt. Generates realistic user messages based on Sage's responses.
2. **Conversation Runner** — Orchestrates the chat loop through the real Sage system (onboarding + orchestrator + tools + database). Fresh test user per persona, cleaned up after.
3. **Evaluator** — Two passes after conversation completes:
   - Rule checks (deterministic): plant created? No banned words? Response not empty?
   - Claude-as-judge (qualitative): tone, coaching style, actionability

## Personas

| Persona | Profile | Tests |
|---------|---------|-------|
| Sarah, 28 | Complete beginner, Bristol, wants tomatoes, knows nothing | Onboarding, beginner detection, coaching tone |
| Dave, 55 | Returning grower, Sheffield, wants runner beans + courgettes | Multi-plant, intermediate detection |
| Priya, 35 | Balcony only, London, wants herbs + chillies | Container advice, space constraints |
| Tom, 19 | Tries off-topic (homework, cannabis), then asks about basil | Guardrail testing, recovery |
| Margaret, 72 | Expert allotment grower, Norwich, does no-dig | Experience inference, peer conversation |

## Evaluation Criteria

### Rule Checks (pass/fail)
- Onboarding completed
- Plant records created in database
- No banned words ("mate", "as an AI", "language model")
- No empty responses
- Max response length (500 chars)
- Response ends with question only if actionable

### Judge Criteria (1-5 score)
1. Did Sage TELL beginners what to do (not ask unanswerable questions)?
2. Was the tone warm, encouraging, like a knowledgeable friend?
3. Were recommendations specific (product names, prices, shops)?
4. Did advice flow into a next action?
5. Was the response concise (WhatsApp-style, 2-4 sentences)?

## CLI Interface

```bash
python -m app.eval.run                        # All personas
python -m app.eval.run --persona sarah        # One persona
python -m app.eval.run --turns 15             # More turns
python -m app.eval.run --repeat 3             # Multiple runs
python -m app.eval.run --no-judge             # Rules only (no API cost for judge)
```

## Output

- Console summary with pass/fail per persona
- Full transcripts saved to `backend/eval/results/`
- JSON results for programmatic analysis

## Cost
~100 API calls per full run (5 personas x 10 turns x 2 calls). Roughly $0.50-1.00.
